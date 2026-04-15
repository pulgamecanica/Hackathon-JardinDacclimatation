class HealthController < ApplicationController
  def show
    render json: {
      status: "ok",
      service: "plume-api",
      time: Time.current.iso8601,
      db: database_ok?
    }
  end

  private

  def database_ok?
    ActiveRecord::Base.connection.execute("SELECT 1")
    true
  rescue StandardError
    false
  end
end
