class CreateGroups < ActiveRecord::Migration[8.1]
  def change
    create_table :groups, id: :uuid do |t|
      t.string :code, null: false
      t.string :name, null: false

      t.timestamps
    end
    add_index :groups, :code, unique: true
  end
end
