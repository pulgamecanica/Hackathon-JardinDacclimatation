require "net/http"

module Api
  module V1
    # Entry point from the calendar form. The front-end submits
    # { visit_date:, party: [{type:, count:}] } and gets back a session the
    # chatbot can immediately work with — no tickets required. Features are
    # agnostic to whether the user has purchased tickets.
    class SessionsController < BaseController
      before_action :load_session, only: %i[show update link_ticket link_group confirm_purchase select_pack]

      def create
        session = VisitSession.new(session_params)
        session.save!
        dispatch_greeting(session)
        render json: serialize(session), status: :created
      end

      def show
        render json: serialize(@session)
      end

      def update
        @session.update!(session_params)
        render json: serialize(@session)
      end

      def link_ticket
        # External ticket code lookup would happen here. Placeholder: attach a
        # confirmed ticket to the session with the provided code metadata.
        ticket = @session.tickets.create!(
          date: params.fetch(:date, @session.visit_date),
          visitor_type: params.fetch(:visitor_type, "adult"),
          purchased: true,
          status: :confirmed,
          purchased_at: Time.current,
          payment_reference: params[:code],
          locked: true
        )
        @session.update!(status: :linked) if @session.draft?
        render json: { session: serialize(@session), ticket: ticket }, status: :created
      end

      def link_group
        @session.link_to_group!(params.require(:code))
        render json: serialize(@session)
      end

      def confirm_purchase
        @session.confirm_purchase!(
          params.require(:ticket_ids),
          params.require(:payment_ref)
        )
        render json: serialize(@session.reload)
      end

      # Materializes a pack offer chosen from the chat into simulated tickets
      # and records the selection under preferences.selected_pack so the
      # agent can reference it later. Non-entry lines (attractions, rentals)
      # don't have a matching ticket shape yet — they're kept in the
      # selected_pack payload so we still have the full context.
      def select_pack
        pack = permitted_pack
        created = Ticket.transaction do
          lines = Array(pack["lines"]).select { |l| PACK_TICKET_VISITOR[l["catalog_id"]] }
          lines.flat_map do |line|
            visitor = PACK_TICKET_VISITOR[line["catalog_id"]]
            qty = line["quantity"].to_i
            next [] if qty <= 0
            qty.times.map do
              @session.tickets.create!(
                date: @session.visit_date,
                visitor_type: visitor,
                purchased: false,
                status: :draft
              )
            end
          end
        end

        @session.preferences = (@session.preferences || {}).merge(
          "selected_pack" => pack.merge("selected_at" => Time.current.iso8601)
        )
        @session.save!

        render json: {
          session: serialize(@session.reload),
          created_ticket_ids: created.map(&:id)
        }, status: :created
      end

      private

      # Map a catalog_id to the Ticket VISITOR_TYPE it should materialize as.
      # Entries that don't map (attractions, rentals, discount entries that
      # share the standard visitor_type) fall back to :adult.
      PACK_TICKET_VISITOR = {
        "entry_standard" => "adult",
        "entry_senior" => "adult",
        "entry_rsa" => "adult",
        "entry_disabled" => "adult",
        "entry_large_family" => "adult",
        "entry_jobseeker" => "adult",
        "entry_small_child" => "small_child",
        "bundle_unlimited" => "adult",
        "bundle_16h" => "adult",
        "bundle_tribe" => "adult"
      }.freeze

      def permitted_pack
        raw = params.require(:pack)
        raw = raw.respond_to?(:permit!) ? raw.permit!.to_h : raw.to_h
        raw
      end

      def load_session
        @session = VisitSession.find(params[:id])
      end

      def session_params
        params.require(:session).permit(
          :visit_date, :status, :user_id, :group_id,
          party: [:type, :count],
          preferences: {}
        )
      end

      def serialize(session)
        {
          id: session.id,
          status: session.status,
          visit_date: session.visit_date,
          party: session.party,
          party_size: session.party_size,
          preferences: session.preferences,
          has_tickets: session.has_tickets?,
          tickets: session.tickets.map { |t| serialize_ticket(t) },
          group_id: session.group_id,
          user_id: session.user_id,
          created_at: session.created_at,
          updated_at: session.updated_at
        }
      end

      def serialize_ticket(ticket)
        {
          id: ticket.id,
          date: ticket.date,
          visitor_type: ticket.visitor_type,
          status: ticket.status,
          purchased: ticket.purchased,
          locked: ticket.locked
        }
      end

      # Fire a proactive welcome message at the orchestrator the moment a
      # session is created. The orchestrator generates the greeting and
      # POSTs it back to /chat_messages/ai_reply; the frontend's existing
      # polling surfaces it without any new plumbing.
      def dispatch_greeting(session)
        uri = URI("#{ai_service_url}/chat/greet")
        body = {
          session_id: session.id.to_s,
          context: greeting_context(session)
        }.to_json

        Thread.new do
          begin
            req = Net::HTTP::Post.new(uri.path)
            req["Content-Type"] = "application/json"
            if ENV["INTERNAL_API_KEY"].present?
              req["Authorization"] = "Bearer #{ENV['INTERNAL_API_KEY']}"
            end
            req.body = body

            Net::HTTP.start(uri.host, uri.port, use_ssl: uri.scheme == "https") do |http|
              http.request(req)
            end
          rescue => e
            Rails.logger.error "[Sessions] Greeting dispatch failed: #{e.message}"
          end
        end
      end

      def greeting_context(session)
        {
          visit_date: session.visit_date,
          party: session.party,
          tickets: session.tickets.map { |t|
            {
              id: t.id, date: t.date, visitor_type: t.visitor_type,
              status: t.status, purchased: t.purchased
            }
          },
          preferences: session.preferences,
          group_id: session.group_id,
          history: []
        }
      end

      def ai_service_url
        ENV.fetch("AI_SERVICE_URL", "http://localhost:8000")
      end
    end
  end
end
