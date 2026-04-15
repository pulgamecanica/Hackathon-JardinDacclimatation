require 'rails_helper'

RSpec.describe MagicLink, type: :model do
  let(:user) { create(:user) }

  describe '.issue!' do
    it 'creates a record, stores only the digest, and returns the raw token' do
      link, raw = MagicLink.issue!(user: user)
      expect(raw).to be_present
      expect(link.token_digest).not_to eq raw
      expect(link.token_digest).to eq Digest::SHA256.hexdigest(raw)
      expect(link.expires_at).to be > Time.current
      expect(link.used_at).to be_nil
    end
  end

  describe '.redeem!' do
    it 'returns the user and marks the link used for a valid token' do
      _link, raw = MagicLink.issue!(user: user)
      expect(MagicLink.redeem!(raw)).to eq user
      # Replay fails — single-use
      expect(MagicLink.redeem!(raw)).to be_nil
    end

    it 'rejects expired tokens' do
      link, raw = MagicLink.issue!(user: user)
      link.update_column(:expires_at, 1.minute.ago)
      expect(MagicLink.redeem!(raw)).to be_nil
    end

    it 'rejects unknown tokens' do
      expect(MagicLink.redeem!("garbage")).to be_nil
    end
  end
end
