module Api
  module V1
    class TicketsController < BaseController
      before_action :load_session

      def index
        render json: @session.tickets.map { |t| serialize(t) }
      end

      # Regular ticket creation (already paid externally).
      def create
        ticket = @session.tickets.create!(ticket_params.merge(purchased: true, status: :confirmed, locked: true))
        render json: serialize(ticket), status: :created
      end

      # Creates a simulated (purchased=false) ticket for planning. Chatbot
      # treats these identically to confirmed tickets.
      def simulated
        ticket = @session.tickets.create!(
          date: params.fetch(:date, @session.visit_date),
          visitor_type: params.fetch(:visitor_type, "adult"),
          purchased: false,
          status: :draft
        )
        render json: serialize(ticket), status: :created
      end

      private

      def load_session
        @session = VisitSession.find(params[:session_id])
      end

      def ticket_params
        params.require(:ticket).permit(:date, :visitor_type, :payment_reference)
      end

      def serialize(ticket)
        {
          id: ticket.id,
          date: ticket.date,
          visitor_type: ticket.visitor_type,
          status: ticket.status,
          purchased: ticket.purchased,
          locked: ticket.locked,
          payment_reference: ticket.payment_reference,
          purchased_at: ticket.purchased_at
        }
      end
    end
  end
end
