Rails.application.routes.draw do
  get "up" => "rails/health#show", as: :rails_health_check
  get "/health", to: "health#show"

  namespace :api do
    namespace :v1 do
      post "auth/request_link", to: "auth#request_link"
      post "auth/verify", to: "auth#verify"

      resources :sessions, only: %i[create show update] do
        member do
          post :link_ticket
          post :link_group
          post :confirm_purchase
          post :select_pack
        end
        resources :chat_messages, only: %i[index create] do
          collection do
            post :ai_reply
          end
        end
        post "chat", to: "chat_messages#chat"
        resources :tickets, only: %i[index create] do
          collection do
            post :simulated
          end
        end
      end

      resources :groups, only: %i[create show]
    end
  end
end
