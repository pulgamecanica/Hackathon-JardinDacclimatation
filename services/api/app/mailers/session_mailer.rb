class SessionMailer < ApplicationMailer
  def magic_link(user, raw_token)
    @user = user
    @url = build_url(raw_token)
    mail(to: user.email, subject: "Your Plume sign-in link")
  end

  private

  def build_url(raw_token)
    base = ENV.fetch("WEB_BASE_URL", "http://localhost:3000")
    "#{base}/auth/verify?token=#{CGI.escape(raw_token)}"
  end
end
