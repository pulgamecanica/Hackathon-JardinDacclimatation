require "net/http"

module Api
  module V1
    # Entry point from the calendar form. The front-end submits
    # { visit_date:, party: [{type:, count:}] } and gets back a session the
    # chatbot can immediately work with — no tickets required. Features are
    # agnostic to whether the user has purchased tickets.
    class SessionsController < BaseController
      before_action :load_session, only: %i[show update link_ticket link_group confirm_purchase]

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

      private

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
