#importing necessary libraries
import streamlit as st
import requests
import json
import sqlite3
from datetime import datetime
import google.generativeai as genai
import os
from fpdf import FPDF

#fitbit api token
FITBIT_API_URL = "https://api.fitbit.com/1/user/-/"
TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyM1BMRDkiLCJzdWIiOiJDN1o0MzciLCJpc3MiOiJGaXRiaXQiLCJ0eXAiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZXMiOiJ3aHIgd3BybyB3bnV0IHdzbGUgd3dlaSB3c29jIHdhY3Qgd3NldCB3bG9jIiwiZXhwIjoxNzI2NDcyMDA4LCJpYXQiOjE3MjYzODU2MDh9.GGLnqigz-AbrmPM4GmTysIjOEz8Tax1FLtSFl4E3HaQ"  # Replace with your Fitbit access token

#authoriation
headers = {
    "Authorization": f"Bearer {TOKEN}"
}

#google generative ai open source key
os.environ["API_KEY"] = "AIzaSyAsDHVYYQXCqlzxgINN_9QE2g65QLFh0Ew"
genai.configure(api_key=os.environ["API_KEY"])

#configure the gen ai model
model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})

#sql database to store the fetched data
conn = sqlite3.connect('fitness_data.db')
cursor = conn.cursor()

#fetch data from fitbit api
def fetch_fitbit_data():
    try:
        #daily activity summary (steps, calories burned)
        activity_url = f"{FITBIT_API_URL}activities/date/today.json"
        activity_data = requests.get(activity_url, headers=headers).json()

        #fetch sleep time
        sleep_url = f"{FITBIT_API_URL}sleep/date/today.json"
        sleep_data = requests.get(sleep_url, headers=headers).json()

        #fetch nutrition (calories consumed)
        food_url = f"{FITBIT_API_URL}foods/log/date/today.json"
        food_data = requests.get(food_url, headers=headers).json()

        #fetching only relevant data
        filtered_data = {
            "date": str(datetime.today().date()),
            "steps": activity_data.get("summary", {}).get("steps", 0),
            "calories_burned": activity_data.get("summary", {}).get("caloriesOut", 0),
            "calories_consumed": food_data.get("summary", {}).get("calories", 0),
            "sleep_duration": sleep_data.get("summary", {}).get("totalMinutesAsleep", 0),
        }

        return filtered_data

    except Exception as e:
        print(f"Error fetching Fitbit data: {e}")
        return None

#function for generating workout plan
#ask user goals for personalised workout recommendation
#prompt for the gen ai model
def generate_formatted_response(fitbit_data, user_goals):
    prompt = f"""
You are a professional fitness coach designing personalized workout plans for users based on their fitness data and goals.

User's current fitness data:
- Steps: {fitbit_data['steps']}
- Calories burned: {fitbit_data['calories_burned']}
- Sleep duration: {fitbit_data['sleep_duration']} minutes
- Calories consumed: {fitbit_data['calories_consumed']}

The user's goals and preferences are as follows:
- Main fitness goal: {user_goals['goal_type']}
- Preferred workout style: {user_goals['workout_preference']}
- Available time per day: {user_goals['time_available']} minutes
- Diet plan requested: {user_goals['formatted_response']}
- Access to weights: {user_goals['weights']}
- Preferred dietary cuisine: {user_goals['diet_cuisine']}

Using this data, generate a structured workout plan. Give the plan only for one day, specifying warm-up exercises, the main workout, and cool-down stretches

Make the plan interactive and motivating, incorporating suggestions for improvement, rest, and recovery.
"""
    

    #enerate response
    response = model.generate_content(prompt)
    formatted_response = response.text.replace(". ", ".\n")

    #save the generated workout in pdf
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 5, txt="personalized workout plan", ln=True)
    pdf.ln(10)

    # Warm-Up
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Warm-Up", ln=True)
    pdf.set_font("Arial", size=12)
    for exercise in formatted_response["warm_up"]:
        pdf.cell(200, 10, txt=f"{exercise['exercise']} - Sets: {exercise['sets']}, Reps: {exercise['reps']}, Duration: {exercise['duration']}", ln=True)

    pdf.ln(5)

    # Main Workout
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Main Workout", ln=True)
    pdf.set_font("Arial", size=12)
    for exercise in formatted_response["main_workout"]:
        pdf.cell(200, 10, txt=f"{exercise['exercise']} - Sets: {exercise['sets']}, Reps: {exercise['reps']}, Intensity: {exercise['intensity']}", ln=True)

    pdf.ln(5)

    # Cool Down
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Cool Down", ln=True)
    pdf.set_font("Arial", size=12)
    for exercise in formatted_response["cool_down"]:
        pdf.cell(200, 10, txt=f"{exercise['exercise']} - Sets: {exercise['sets']}, Reps: {exercise['reps']}, Intensity: {exercise['intensity']}", ln=True)

    pdf.ln(10)

    # Add Diet Plan Section
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Diet Plan", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Breakfast: {formatted_response['breakfast']}", ln=True)
    pdf.cell(200, 10, txt=f"Lunch: {formatted_response['lunch']}", ln=True)
    pdf.cell(200, 10, txt=f"Dinner: {formatted_response['dinner']}", ln=True)
    pdf.cell(200, 10, txt=f"Snacks: {formatted_response['snacks']}", ln=True)

    pdf.output("generated_formatted_response.pdf")

    print("Generated workout plan has been saved to 'generated_formatted_response.pdf'.")

#main function
def main():
    st.title("Fitness Coach")
    st.subheader("Get your personalized workout plan")

    fitbit_data = fetch_fitbit_data()

    if fitbit_data:
        #disply the current user data
        st.write("Your current fitness data:")
        st.write(f"Steps: {fitbit_data['steps']}")
        st.write(f"Calories burned: {fitbit_data['calories_burned']}")
        st.write(f"Sleep duration: {fitbit_data['sleep_duration']} minutes")
        st.write(f"Calories consumed: {fitbit_data['calories_consumed']}")

        #ask user to input desired goals
        user_goals = {
            "goal_type": st.selectbox("What is your main fitness goal?", ["Weight Loss", "Muscle Gain", "Endurance", "Flexibility"]),
            "workout_preference": st.selectbox("What type of workout do you prefer?", ["Yoga", "Running", "Swimming", "Cycling"]),
            "time_available": st.slider("How many minutes do you have available for workout per day?", 30, 120, 60),
            "formatted_response": st.selectbox("Do you want a diet plan?", ["Yes", "No"]),
            "weights": st.selectbox("Do you have access to weights?", ["Yes", "No"]),
            "diet_cuisine": st.selectbox("What type of cuisine do you prefer?", ["Indian", "Italian", "Chinese", "Mexican"])
        }

        if st.button("Generate Workout Plan"):
            generate_formatted_response(fitbit_data, user_goals)
            st.write("Your workout plan has been generated. Please check the 'generated_formatted_response.pdf' file.")

    conn.close()
    
if __name__ == "__main__": 
    main()
