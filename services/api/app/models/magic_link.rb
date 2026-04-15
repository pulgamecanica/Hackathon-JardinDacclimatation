require "digest"

class MagicLink < ApplicationRecord
  belongs_to :user

  TOKEN_LIFETIME = 15.minutes

  scope :active, -> { where(used_at: nil).where("expires_at > ?", Time.current) }

  # Generates a new magic link for the given user and returns [record, raw_token].
  # Only the digest is stored; the raw token is what we email.
  def self.issue!(user:, ip: nil, user_agent: nil)
    raw = SecureRandom.urlsafe_base64(32)
    link = create!(
      user: user,
      token_digest: Digest::SHA256.hexdigest(raw),
      expires_at: TOKEN_LIFETIME.from_now,
      requested_ip: ip,
      user_agent: user_agent
    )
    [link, raw]
  end

  def self.redeem!(raw_token)
    digest = Digest::SHA256.hexdigest(raw_token.to_s)
    link = active.find_by(token_digest: digest)
    return nil unless link

    link.update!(used_at: Time.current)
    link.user
  end

  def expired?
    expires_at <= Time.current
  end

  def used?
    used_at.present?
  end
end
