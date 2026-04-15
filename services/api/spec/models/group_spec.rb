require 'rails_helper'

RSpec.describe Group, type: :model do
  describe 'validations' do
    subject { build(:group) }
    it { is_expected.to validate_presence_of(:name) }
  end

  it 'auto-generates a code on create' do
    group = create(:group)
    expect(group.code).to be_present
    expect(group.code.length).to eq 8
  end

  it 'enforces unique codes' do
    g1 = create(:group)
    dupe = build(:group, code: g1.code)
    expect(dupe).not_to be_valid
  end
end
