require 'rails_helper'

RSpec.describe VisitSession, type: :model do
  describe 'associations' do
    it { is_expected.to belong_to(:user).optional }
    it { is_expected.to belong_to(:group).optional }
    it { is_expected.to have_many(:tickets).dependent(:destroy) }
    it { is_expected.to have_many(:chat_messages).dependent(:destroy) }
  end

  describe 'validations' do
    it { is_expected.to validate_presence_of(:visit_date) }

    it 'requires at least one visitor in the party' do
      session = build(:visit_session, party: [])
      expect(session).not_to be_valid
      expect(session.errors[:party]).to include("must include at least one visitor")
    end

    it 'counts visitors across party entries' do
      session = build(:visit_session, party: [{ "type" => "adult", "count" => 3 }])
      expect(session.party_size).to eq 3
    end
  end

  describe 'agnostic features' do
    it 'is valid without any tickets (calendar-only session)' do
      session = build(:visit_session)
      expect(session).to be_valid
      expect(session.has_tickets?).to be false
    end

    it 'defaults preferences on create' do
      session = create(:visit_session, preferences: {})
      expect(session.preferences).to include("mobility" => "standard", "pace" => "relaxed")
    end
  end

  describe '#confirm_purchase!' do
    it 'promotes simulated tickets and links the session' do
      session = create(:visit_session)
      sim1 = create(:ticket, :simulated, visit_session: session)
      sim2 = create(:ticket, :simulated, visit_session: session)

      session.confirm_purchase!([sim1.id, sim2.id], "stripe_ref_abc")

      expect(sim1.reload).to be_purchased
      expect(sim1.reload).to be_confirmed
      expect(sim1.reload.locked).to be true
      expect(session.reload).to be_linked
    end
  end
end
