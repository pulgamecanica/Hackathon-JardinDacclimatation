class AddMetadataToChatMessages < ActiveRecord::Migration[8.1]
  def change
    add_column :chat_messages, :metadata, :jsonb, default: {}
  end
end
