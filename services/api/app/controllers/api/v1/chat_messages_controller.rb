require "net/http"

module Api
  module V1
    class ChatMessagesController < BaseController
      before_action :load_session

      # GET /api/v1/sessions/:session_id/chat_messages
      def index
        messages = @session.chat_messages.order(:created_at, :id)
        if params[:after].present?
          pivot = @session.chat_messages.find_by(id: params[:after])
          # UUIDs aren't time-sortable — pivot on timestamp instead.
          messages = messages.where("created_at > ?", pivot.created_at) if pivot
        end
        render json: messages.map { |m| serialize(m) }
      end

      # POST /api/v1/sessions/:session_id/chat_messages
      def create
        msg = @session.chat_messages.create!(message_params)
        render json: serialize(msg), status: :created
      end

      # POST /api/v1/sessions/:session_id/chat
      # Persists the user message, dispatches to the AI orchestrator via
      # Celery (async), and returns immediately. The frontend polls for
      # the assistant reply via GET index?after=:id.
      def chat
        user_msg = @session.chat_messages.create!(
          role: "user",
          content: params.require(:message)
        )

        context = build_context
        dispatch_to_orchestrator(params[:message], context)

        render json: {
          chat_message: serialize(user_msg),
          status: "processing"
        }, status: :accepted
      end

      # POST /api/v1/sessions/:session_id/chat_messages/ai_reply
      # Internal-only callback — the orchestrator calls this when the
      # Celery task finishes to persist the assistant message.
      def ai_reply
        require_internal!

        content = params.require(:content)
        agent = params[:agent]
        suggestions = Array(params[:suggestions]).map(&:to_s).reject(&:blank?)
        packs = normalize_packs(params[:packs])

        meta = { agent: agent }.compact
        meta[:suggestions] = suggestions if suggestions.any?
        meta[:packs] = packs if packs.any?

        msg = @session.chat_messages.create!(
          role: "assistant",
          content: content,
          metadata: meta
        )

        render json: serialize(msg), status: :created
      end

      private

      def load_session
        @session = VisitSession.includes(:tickets).find(params[:session_id])
      end

      def message_params
        params.require(:chat_message).permit(:role, :content)
      end

      # Normalize a list of pack hashes into plain primitives so the
      # metadata jsonb column stays predictable. Unknown keys are dropped.
      def normalize_packs(raw)
        return [] if raw.blank?
        Array(raw).filter_map do |pack|
          next nil unless pack.is_a?(ActionController::Parameters) || pack.is_a?(Hash)
          hash = pack.respond_to?(:permit) ? pack.permit!.to_h : pack.to_h
          lines = Array(hash["lines"] || hash[:lines]).map do |line|
            line_h = line.respond_to?(:permit) ? line.permit!.to_h : line.to_h
            {
              catalog_id: line_h["catalog_id"] || line_h[:catalog_id],
              name_fr: line_h["name_fr"] || line_h[:name_fr],
              category: line_h["category"] || line_h[:category],
              quantity: (line_h["quantity"] || line_h[:quantity]).to_i,
              unit_price_eur: (line_h["unit_price_eur"] || line_h[:unit_price_eur]).to_f,
              subtotal_eur: (line_h["subtotal_eur"] || line_h[:subtotal_eur]).to_f
            }
          end
          {
            id: hash["id"] || hash[:id],
            name: hash["name"] || hash[:name],
            description: hash["description"] || hash[:description],
            total_eur: (hash["total_eur"] || hash[:total_eur]).to_f,
            currency: hash["currency"] || hash[:currency] || "EUR",
            recommended: !!(hash["recommended"] || hash[:recommended]),
            highlight_features: Array(hash["highlight_features"] || hash[:highlight_features]).map(&:to_s),
            lines: lines
          }
        end
      end

      def serialize(msg)
        {
          id: msg.id,
          role: msg.role,
          content: msg.content,
          metadata: msg.try(:metadata),
          created_at: msg.created_at
        }
      end

      def build_context
        history = @session.chat_messages.last(16).map do |m|
          { role: m.role, content: m.content }
        end

        tickets = @session.tickets.map do |t|
          {
            id: t.id,
            date: t.date,
            visitor_type: t.visitor_type,
            status: t.status,
            purchased: t.purchased
          }
        end

        {
          visit_date: @session.visit_date,
          party: @session.party,
          tickets: tickets,
          preferences: @session.preferences,
          group_id: @session.group_id,
          history: history
        }
      end

      def ai_service_url
        ENV.fetch("AI_SERVICE_URL", "http://localhost:8000")
      end

      def dispatch_to_orchestrator(message, context)
        uri = URI("#{ai_service_url}/chat/async")
        body = {
          session_id: @session.id.to_s,
          message: message,
          context: context
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
            Rails.logger.error "[ChatMessages] Failed to dispatch to orchestrator: #{e.message}"
          end
        end
      end
    end
  end
end
