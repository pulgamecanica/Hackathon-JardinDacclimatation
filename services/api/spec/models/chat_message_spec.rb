require 'rails_helper'

RSpec.describe ChatMessage, type: :model do
  describe 'validations' do
    subject { build(:chat_message) }
    it { is_expected.to validate_presence_of(:content) }
    it { is_expected.to validate_inclusion_of(:role).in_array(ChatMessage::ROLES) }
    it { is_expected.to belong_to(:visit_session) }
  end
end
