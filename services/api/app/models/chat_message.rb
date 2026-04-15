class ChatMessage < ApplicationRecord
  ROLES = %w[user assistant system tool].freeze

  belongs_to :visit_session

  validates :role, presence: true, inclusion: { in: ROLES }
  validates :content, presence: true
end
