class SessionMailer < ApplicationMailer
  # The magic link points to the FRONTEND (Next.js). The frontend route
  # reads the token from the URL, POSTs it to /api/v1/auth/verify, stores
  # the returned JWT, and loads the user's conversation. The API URL is
  # never exposed in the email — clients don't know about the backend.
  def magic_link(user, raw_token)
    @user = user
    @url = build_url(raw_token)
    mail(to: user.email, subject: "Your Plume sign-in link")
  end

  private

  def build_url(raw_token)
    frontend = ENV.fetch("FRONTEND_URL", "http://localhost:3000")
    path     = ENV.fetch("FRONTEND_AUTH_VERIFY_PATH", "/auth/verify")
    "#{frontend}#{path}?token=#{CGI.escape(raw_token)}"
  end
end
