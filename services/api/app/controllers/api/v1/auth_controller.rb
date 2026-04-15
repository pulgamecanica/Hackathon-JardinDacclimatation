module Api
  module V1
    # Passwordless auth: request a magic link by email, verify by clicking it.
    # On verify we return a signed JWT the client stores as its auth token.
    class AuthController < BaseController
      def request_link
        email = params.require(:email).to_s.downcase.strip
        user = User.find_or_create_by!(email: email) do |u|
          # password_digest is required by has_secure_password but isn't used
          # for login; we seed it with a random value so the record is valid.
          u.password = SecureRandom.hex(16)
        end

        link, raw = MagicLink.issue!(
          user: user,
          ip: request.remote_ip,
          user_agent: request.user_agent
        )
        SessionMailer.magic_link(user, raw).deliver_later

        # Always return 202 regardless of whether the account existed, so
        # attackers can't enumerate registered emails.
        render json: { status: "sent", expires_at: link.expires_at }, status: :accepted
      end

      def verify
        user = MagicLink.redeem!(params.require(:token))
        return render(json: { error: "invalid_or_expired" }, status: :unauthorized) unless user

        token = JWT.encode(
          { sub: user.id, email: user.email, exp: 7.days.from_now.to_i, iat: Time.current.to_i },
          jwt_secret,
          "HS256"
        )
        render json: { token: token, user: { id: user.id, email: user.email } }
      end

      private

      def jwt_secret
        ENV.fetch("JWT_SECRET") { Rails.application.secret_key_base }
      end
    end
  end
end
