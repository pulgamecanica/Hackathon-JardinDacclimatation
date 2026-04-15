require 'rails_helper'

RSpec.describe Ticket, type: :model do
  describe 'validations' do
    it { is_expected.to validate_presence_of(:date) }
    it { is_expected.to validate_presence_of(:visitor_type) }
    it { is_expected.to validate_inclusion_of(:visitor_type).in_array(Ticket::VISITOR_TYPES) }
    it { is_expected.to belong_to(:visit_session) }
  end

  describe 'simulated vs purchased' do
    let(:session) { create(:visit_session) }

    it 'creates simulated ticket with purchased=false' do
      ticket = create(:ticket, :simulated, visit_session: session)
      expect(ticket).to be_simulated
      expect(ticket).to be_draft
      expect(ticket.purchased).to be false
    end

    it 'locks ticket after confirmation' do
      ticket = create(:ticket, :simulated, visit_session: session)
      ticket.confirm!('stripe_123')

      expect(ticket.reload).to be_confirmed
      expect(ticket.reload.purchased).to be true
      expect(ticket.reload.locked).to be true
      expect(ticket.reload.payment_reference).to eq 'stripe_123'
    end

    it 'prevents changes to confirmed tickets' do
      ticket = create(:ticket, :confirmed, visit_session: session)
      ticket.date = Date.current + 2.days
      expect(ticket).not_to be_valid
      expect(ticket.errors[:base]).to include("Confirmed tickets cannot be modified")
    end
  end

  describe 'scopes' do
    let(:session) { create(:visit_session) }

    it 'separates simulated and bought' do
      sim = create(:ticket, :simulated, visit_session: session)
      paid = create(:ticket, :confirmed, visit_session: session)
      expect(Ticket.simulated).to include(sim)
      expect(Ticket.simulated).not_to include(paid)
      expect(Ticket.bought).to include(paid)
    end
  end
end
