class CreateTickets < ActiveRecord::Migration[8.1]
  def change
    create_table :tickets, id: :uuid do |t|
      t.references :visit_session, null: false, foreign_key: true, type: :uuid
      t.date :date, null: false
      t.string :visitor_type, null: false
      t.integer :status, null: false, default: 0
      t.boolean :purchased, null: false, default: false
      t.datetime :purchased_at
      t.string :payment_reference
      t.boolean :locked, null: false, default: false

      t.timestamps
    end

    add_index :tickets, :purchased
    add_index :tickets, %i[visit_session_id status]
  end
end
