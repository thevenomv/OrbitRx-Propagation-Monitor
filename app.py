import tkinter as tk
from tkinter import messagebox

# 1. This function tells the button what to do when clicked
def show_message():
    messagebox.showinfo("Success!", "Look at me, I made a Python App!")

# 2. Create the main window
window = tk.Tk()
window.title("My First App")
window.geometry("300x200") # Sets the width and height

# 3. Create a button and put it in the window
button = tk.Button(window, text="Click Me!", command=show_message)
button.pack(pady=50) # 'pack' places it in the window, 'pady' adds space around it

# 4. Keep the window running until you close it
window.mainloop()