class CreateVisitSessions < ActiveRecord::Migration[8.1]
  def change
    create_table :visit_sessions, id: :uuid do |t|
      t.integer :status, null: false, default: 0
      t.references :user, null: true, foreign_key: true, type: :uuid
      t.references :group, null: true, foreign_key: true, type: :uuid
      t.date :visit_date
      t.jsonb :party, null: false, default: []
      t.jsonb :preferences, null: false, default: {}

      t.timestamps
    end

    add_index :visit_sessions, :status
    add_index :visit_sessions, :visit_date
  end
end
