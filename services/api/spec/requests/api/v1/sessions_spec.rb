require 'rails_helper'

RSpec.describe "Api::V1::Sessions", type: :request do
  describe "POST /api/v1/sessions" do
    it "creates a draft session from the calendar form without any tickets" do
      post "/api/v1/sessions", params: {
        session: {
          visit_date: (Date.current + 7).iso8601,
          party: [{ type: "adult", count: 2 }, { type: "child", count: 1 }]
        }
      }

      expect(response).to have_http_status(:created)
      body = JSON.parse(response.body)
      expect(body["status"]).to eq "draft"
      expect(body["party_size"]).to eq 3
      expect(body["has_tickets"]).to be false
      expect(body["id"]).to be_present
    end

    it "rejects an empty party" do
      post "/api/v1/sessions", params: {
        session: { visit_date: Date.current.iso8601, party: [] }
      }
      expect(response).to have_http_status(:unprocessable_content).or have_http_status(:unprocessable_entity)
    end
  end

  describe "POST /api/v1/sessions/:id/confirm_purchase" do
    it "promotes simulated tickets to purchased" do
      session = create(:visit_session)
      ticket = create(:ticket, :simulated, visit_session: session)

      post "/api/v1/sessions/#{session.id}/confirm_purchase",
           params: { ticket_ids: [ticket.id], payment_ref: "stripe_xyz" }

      expect(response).to have_http_status(:ok)
      expect(ticket.reload).to be_confirmed
      expect(ticket.reload.purchased).to be true
    end
  end
end
