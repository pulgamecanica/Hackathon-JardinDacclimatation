FactoryBot.define do
  factory :ticket do
    visit_session
    date { Date.current + 7 }
    visitor_type { "adult" }
    status { :draft }
    purchased { false }
    locked { false }

    trait :simulated do
      purchased { false }
      status { :draft }
      locked { false }
    end

    trait :confirmed do
      purchased { true }
      status { :confirmed }
      locked { true }
      purchased_at { Time.current }
      payment_reference { "stripe_test_123" }
    end
  end
end
