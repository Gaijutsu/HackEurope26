import resend

def send_local_test():
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",  # Keep this for sandbox
            "to": "gaijutsu24@gmail.com",    # Must be your signup email
            "subject": "Local Host Test",
            "html": "<p>Sent from my local machine!</p>"
        })
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
