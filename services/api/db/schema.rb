# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_04_15_224070) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "pg_catalog.plpgsql"
  enable_extension "pgcrypto"

  create_table "chat_messages", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.text "content", null: false
    t.datetime "created_at", null: false
    t.string "role", null: false
    t.datetime "updated_at", null: false
    t.uuid "visit_session_id", null: false
    t.index ["visit_session_id", "created_at"], name: "index_chat_messages_on_visit_session_id_and_created_at"
    t.index ["visit_session_id"], name: "index_chat_messages_on_visit_session_id"
  end

  create_table "groups", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.string "code", null: false
    t.datetime "created_at", null: false
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.index ["code"], name: "index_groups_on_code", unique: true
  end

  create_table "magic_links", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.datetime "created_at", null: false
    t.datetime "expires_at", null: false
    t.string "requested_ip"
    t.string "token_digest", null: false
    t.datetime "updated_at", null: false
    t.datetime "used_at"
    t.string "user_agent"
    t.uuid "user_id", null: false
    t.index ["expires_at"], name: "index_magic_links_on_expires_at"
    t.index ["token_digest"], name: "index_magic_links_on_token_digest", unique: true
    t.index ["user_id"], name: "index_magic_links_on_user_id"
  end

  create_table "tickets", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.datetime "created_at", null: false
    t.date "date", null: false
    t.boolean "locked", default: false, null: false
    t.string "payment_reference"
    t.boolean "purchased", default: false, null: false
    t.datetime "purchased_at"
    t.integer "status", default: 0, null: false
    t.datetime "updated_at", null: false
    t.uuid "visit_session_id", null: false
    t.string "visitor_type", null: false
    t.index ["purchased"], name: "index_tickets_on_purchased"
    t.index ["visit_session_id", "status"], name: "index_tickets_on_visit_session_id_and_status"
    t.index ["visit_session_id"], name: "index_tickets_on_visit_session_id"
  end

  create_table "users", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "email", null: false
    t.string "password_digest", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], name: "index_users_on_email", unique: true
  end

  create_table "visit_sessions", id: :uuid, default: -> { "gen_random_uuid()" }, force: :cascade do |t|
    t.datetime "created_at", null: false
    t.uuid "group_id"
    t.jsonb "party", default: [], null: false
    t.jsonb "preferences", default: {}, null: false
    t.integer "status", default: 0, null: false
    t.datetime "updated_at", null: false
    t.uuid "user_id"
    t.date "visit_date"
    t.index ["group_id"], name: "index_visit_sessions_on_group_id"
    t.index ["status"], name: "index_visit_sessions_on_status"
    t.index ["user_id"], name: "index_visit_sessions_on_user_id"
    t.index ["visit_date"], name: "index_visit_sessions_on_visit_date"
  end

  add_foreign_key "chat_messages", "visit_sessions"
  add_foreign_key "magic_links", "users"
  add_foreign_key "tickets", "visit_sessions"
  add_foreign_key "visit_sessions", "groups"
  add_foreign_key "visit_sessions", "users"
end
