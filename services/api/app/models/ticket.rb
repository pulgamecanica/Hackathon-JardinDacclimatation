class Ticket < ApplicationRecord
  belongs_to :visit_session

  VISITOR_TYPES = %w[adult small_child child teen].freeze

  enum :status, { draft: 0, reserved: 1, confirmed: 2, used: 3, expired: 4 }, default: :draft

  validates :date, presence: true
  validates :visitor_type, presence: true, inclusion: { in: VISITOR_TYPES }
  validates :purchased, inclusion: { in: [true, false] }
  validate :immutable_if_confirmed, on: :update

  scope :simulated, -> { where(purchased: false) }
  scope :bought,    -> { where(purchased: true) }

  def simulated? = !purchased?

  def confirm!(payment_ref)
    return false if confirmed? && purchased?

    update!(
      purchased: true,
      status: :confirmed,
      purchased_at: Time.current,
      payment_reference: payment_ref,
      locked: true
    )
  end

  private

  def immutable_if_confirmed
    return unless status_was == "confirmed"

    if date_changed? || visitor_type_changed?
      errors.add(:base, "Confirmed tickets cannot be modified")
    end
  end
end
