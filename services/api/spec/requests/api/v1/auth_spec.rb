require 'rails_helper'

RSpec.describe "Api::V1::Auth", type: :request do
  describe "POST /api/v1/auth/request_link" do
    it "creates the user on first request and queues an email" do
      expect {
        post "/api/v1/auth/request_link", params: { email: "new@example.com" }
      }.to change(User, :count).by(1)
       .and change(MagicLink, :count).by(1)
       .and have_enqueued_mail(SessionMailer, :magic_link)

      expect(response).to have_http_status(:accepted)
    end

    it "does not enumerate existing emails (always 202)" do
      create(:user, email: "existing@example.com")
      post "/api/v1/auth/request_link", params: { email: "existing@example.com" }
      expect(response).to have_http_status(:accepted)
    end
  end

  describe "POST /api/v1/auth/verify" do
    let(:user) { create(:user) }

    it "returns a JWT for a valid token" do
      _link, raw = MagicLink.issue!(user: user)
      post "/api/v1/auth/verify", params: { token: raw }
      expect(response).to have_http_status(:ok)
      body = JSON.parse(response.body)
      expect(body["token"]).to be_present
      expect(body.dig("user", "email")).to eq user.email
    end

    it "rejects invalid tokens" do
      post "/api/v1/auth/verify", params: { token: "nope" }
      expect(response).to have_http_status(:unauthorized)
    end
  end
end
