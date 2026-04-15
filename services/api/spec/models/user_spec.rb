require 'rails_helper'

RSpec.describe User, type: :model do
  describe 'validations' do
    subject { build(:user) }
    it { is_expected.to validate_presence_of(:email) }
    it { is_expected.to validate_uniqueness_of(:email).case_insensitive }

    it 'normalizes email to lowercase on save' do
      user = create(:user, email: "Foo@Example.COM")
      expect(user.email).to eq "foo@example.com"
    end
  end
end
