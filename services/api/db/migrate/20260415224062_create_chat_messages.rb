class CreateChatMessages < ActiveRecord::Migration[8.1]
  def change
    create_table :chat_messages, id: :uuid do |t|
      t.references :visit_session, null: false, foreign_key: true, type: :uuid
      t.string :role, null: false
      t.text :content, null: false

      t.timestamps
    end

    add_index :chat_messages, %i[visit_session_id created_at]
  end
end
