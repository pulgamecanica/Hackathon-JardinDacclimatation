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
    end
  end
end
