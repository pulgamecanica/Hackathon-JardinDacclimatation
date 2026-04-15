module Api
  module V1
    class ChatMessagesController < BaseController
      before_action :load_session

      def index
        render json: @session.chat_messages.map { |m| serialize(m) }
      end

      def create
        msg = @session.chat_messages.create!(message_params)
        render json: serialize(msg), status: :created
      end

      private

      def load_session
        @session = VisitSession.find(params[:session_id])
      end

      def message_params
        params.require(:chat_message).permit(:role, :content)
      end

      def serialize(msg)
        { id: msg.id, role: msg.role, content: msg.content, created_at: msg.created_at }
      end
    end
  end
end
