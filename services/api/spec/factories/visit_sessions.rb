FactoryBot.define do
  factory :visit_session do
    status { :draft }
    visit_date { Date.current + 7 }
    party { [{ "type" => "adult", "count" => 2 }, { "type" => "child", "count" => 1 }] }
    preferences { {} }
  end
end
