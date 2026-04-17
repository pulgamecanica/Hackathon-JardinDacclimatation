class ApplicationMailer < ActionMailer::Base
  default from: ENV.fetch("MAIL_FROM", "pavo@jardindacclimatation.fr")
  layout "mailer"
end
