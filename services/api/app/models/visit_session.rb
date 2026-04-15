class VisitSession < ApplicationRecord
  belongs_to :user, optional: true
  belongs_to :group, optional: true

  has_many :tickets, dependent: :destroy
  has_many :chat_messages, -> { order(created_at: :asc) }, dependent: :destroy

  enum :status, { draft: 0, linked: 1, active: 2, completed: 3 }, default: :draft

  validates :visit_date, presence: true
  validate :party_has_at_least_one_visitor

  before_validation :set_default_preferences, on: :create

  scope :for_date, ->(date) { where(visit_date: date) }

  # Agnostic helpers: features work whether or not tickets are purchased.
  def simulated_tickets = tickets.where(purchased: false)
  def confirmed_tickets = tickets.where(purchased: true, status: Ticket.statuses[:confirmed])

  def party_size
    Array(party).sum { |entry| entry.is_a?(Hash) ? entry["count"].to_i : 0 }
  end

  def has_tickets? = tickets.exists?

  def confirm_purchase!(ticket_ids, payment_ref)
    transaction do
      tickets.where(id: ticket_ids, purchased: false).find_each do |ticket|
        ticket.confirm!(payment_ref)
      end
      update!(status: :linked) if draft?
    end
  end

  def link_to_group!(group_code)
    self.group = Group.find_by!(code: group_code)
    save!
  end

  private

  def set_default_preferences
    self.preferences ||= {}
    self.preferences.reverse_merge!(
      "mobility" => "standard",
      "pace" => "relaxed",
      "interests" => %w[family nature],
      "notifications" => true
    )
  end

  def party_has_at_least_one_visitor
    return errors.add(:party, "must be an array") unless party.is_a?(Array)
    return errors.add(:party, "must include at least one visitor") if party.empty?

    total = party.sum { |entry| entry.is_a?(Hash) ? entry["count"].to_i : 0 }
    errors.add(:party, "must include at least one visitor") if total < 1
  end
end
