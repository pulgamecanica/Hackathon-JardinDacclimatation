class ApplicationMailer < ActionMailer::Base
  default from: ENV.fetch("MAIL_FROM", "plume@jardindacclimatation.fr")
  layout "mailer"
end
