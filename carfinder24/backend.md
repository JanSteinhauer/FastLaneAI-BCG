We need to create a more precise backend and filtering process:
* The user should be led through a decision process (from vague -> specific):
  1. What type of vehicle: size, body_type? Preference for fuel type? Transmission?
  2. If user has no idea, start a new process:
    2.1 What does the user need the car for (family, personal, job, travel). Ask about circumstances: can the user charge an electric vehicle
    2.2 What where previous cars they have driven
    2.3 Explain what type of car would be good for the use case
  3. Comsetic aspects: color, body_type
  4. Car mileage and usage condition
  5. Price range, as well as leasing or purchase
    5.1 If leasing, ask for conditions (term length, leasing mileage)
  6. Give the user a summary of the choices they made, or if we suggested a car, then summarize why that specific car was chosen
* The agent needs to ask what terms of leasing the user wants (choose from buckets of 12, 24, 36, 48 months - see the model.py file) as well as km_tiers
* Write tests for user trying invalid inputs (such as wrong km_tier, or invalid terms, too low minimum price, wrong max_down_payment_share)
  * If user asks for invalid input for terms and tiers, display error
* Hardcode a function to respond to user asking about how leasing agreement is calculated showing all details (as transparent as possible)
* If invalid input is detected, do not proceed with sale and tell user about possible choices. For example, display possible leasing durations
* At the end of the process, once the user has chosen a car, they have exactly three options:
  1. Do nothing and look at the offer in the app
  2. (default) Send an email with the details of the offer, but no legal document
  3. If the user specifically asks to have a leasing agreement, then create a PDF of it and send it as an attachment in the email next to the offer details
* Regardless of the user's tone, the agent must remain neutral and on topic: it should talk as a kind car salesman
* Priotize premium dealers when suggesting cars (dealers that have an agreement with CarFinder24)
* Create a deterministic function for calculating the deal quality (fairer Preis / guter Preis, sehr guter Preis):
  * identify peer group based on model, vehicle_type, body_type, mileage and age
  * calculate average price of peer group and rank our offer against peer group on a scale of 0.0 - 5.0 (5.0 is best, a VERY good deal)