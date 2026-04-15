class Group < ApplicationRecord
  has_many :visit_sessions, dependent: :nullify

  validates :code, presence: true, uniqueness: true
  validates :name, presence: true

  before_validation :generate_code, on: :create

  private

  def generate_code
    self.code ||= SecureRandom.alphanumeric(8).upcase
  end
end
