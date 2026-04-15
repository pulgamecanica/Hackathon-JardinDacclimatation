class ApplicationController < ActionController::API
  rescue_from ActiveRecord::RecordNotFound do |e|
    render json: { error: "not_found", message: e.message }, status: :not_found
  end

  rescue_from ActiveRecord::RecordInvalid do |e|
    render json: { error: "validation_failed", details: e.record.errors.as_json }, status: :unprocessable_entity
  end

  rescue_from ActionController::ParameterMissing do |e|
    render json: { error: "parameter_missing", param: e.param }, status: :bad_request
  end

  private

  def internal_request?
    return true unless ENV["INTERNAL_API_KEY"].present?
    ActiveSupport::SecurityUtils.secure_compare(
      request.headers["Authorization"].to_s.sub("Bearer ", ""),
      ENV["INTERNAL_API_KEY"]
    )
  end

  def require_internal!
    head :unauthorized unless internal_request?
  end
end
