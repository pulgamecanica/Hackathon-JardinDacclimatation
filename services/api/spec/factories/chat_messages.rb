FactoryBot.define do
  factory :chat_message do
    visit_session
    role { "user" }
    content { "Bonjour Plume !" }
  end
end
