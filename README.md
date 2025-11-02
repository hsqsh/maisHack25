# 👁️ Les Yeux: Visual Search App

## 🌟 Inspiration

For people who are visually impaired, navigating their surroundings and locating specific objects can be challenging. Whether indoors or outdoors, they often require assistance to find items like water bottles, phones, or elevators. This inspired us to create "Les Yeux," a visual search app that empowers users to locate objects independently.

## 🔍 What It Does

Using audio input, the user specifies the object they want to find. The app scans the surroundings using the device's camera to detect the specified object. Once detected, the app provides feedback through a beep, indicating the direction.

## 🛠️ How We Built It

- **Backend**: We utilized YOLOv8n for general object detection and trained a custom model specifically for STM elevator sign detection. The dataset, consisting of 102 photos, was created and labeled by our team using Roboflow. Preprocessing and augmentation techniques were applied to enhance the model's generalization capabilities.
- **Frontend**: Built with Vue.js, the user interface is designed for maximum ease of use. The frontend accesses the camera and microphone through APIs and communicates with the backend via predefined endpoints. Vue.js state management is used to track application status, such as recording activity.

## 🚧 Challenges We Faced

1. **Platform Choice**: Initially, we planned to develop an Android app, but speech recognition was not feasible on the devices we had. We pivoted to a web application instead.
2. **Integration Issues**: The model's accuracy dropped significantly when integrating the frontend and backend. We implemented patches in the frontend to address this.
3. **Model Training**: Training a model is time-intensive. Instead of merging the STM elevator sign detection into the general model, we opted to use two models (YOLOv8n and our custom model) in parallel, achieving the same outcome.

## 🏆 Accomplishments

- Created and labeled our own dataset.
- Successfully trained a custom computer vision model for STM elevator sign detection.
- Developed a functional and user-friendly web application.

## 📚 What We Learned

- How to create and label datasets.
- Training computer vision models.
- Building a frontend application using Vue.js.

## 🚀 What's Next

- Deploy the app as a shortcut accessible on mobile devices.
- Further optimize the models for faster and more accurate detection.

## 🧩 Built With

- **JavaScript**
- **Node.js**
- **Vue.js**
- **YOLOv8**

## 🏅 Submitted To

- MAIS Hacks 25-26

---

We hope "Les Yeux" can make a meaningful difference in the lives of visually impaired individuals by providing them with greater independence and confidence in their daily activities. ✨
