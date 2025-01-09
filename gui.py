import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import logging
from workflow_utils import process_files, extract_text_from_pdf_no_ocr, chat_with_pdf, create_anki_deck
from workflow_utils import *
from pathlib import Path
from threading import Thread
import tempfile
import shutil
import time
import functools
import google.generativeai as genai
import webbrowser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AppGUI:
    def __init__(self, master):
        self.master = master
        master.title("Document to Anki Deck Creator")
        master.geometry("600x600")  # Initial window size
        master.minsize(600, 600)  # Set minimum size for responsiveness
        master.columnconfigure(0, weight=1)  # Configure the main window's column to expand
        master.rowconfigure(5, weight=1)  # Configure the last row to occupy space in the middle
        self.input_path = tk.StringVar()
        self.pages_per_pdf = tk.IntVar(value=500)
        self.use_ocr = tk.BooleanVar(value=False)
        self.pdf_engine = tk.StringVar(value="fpdf")
        self.data_file = tk.StringVar(value="data.txt")
        self.anki_output = tk.StringVar(value="output.apkg")
        self.ai_model = tk.StringVar(value="gemini-2.0-flash-exp")  # Default AI model
        self.api_key = tk.StringVar()
        self.chat_windows = {}  # Store a reference to the chat windows.
        self.start_button = None
        self.create_widgets()
        self.pending_chats = 0  # Tracks how many chat windows are still open

    def create_widgets(self):
        # Input File/Dir Section
        input_frame = ttk.LabelFrame(self.master, text="Input File or Directory")
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(input_frame, text="Input Path:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.input_path, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        ttk.Button(input_frame, text="Browse", command=self.browse_files).grid(row=0, column=2, padx=5, pady=5)

        # Options Section
        options_frame = ttk.LabelFrame(self.master, text="Options")
        options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(options_frame, text="Pages per PDF:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(options_frame, textvariable=self.pages_per_pdf, width=10).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Checkbutton(options_frame, text="Use OCR", variable=self.use_ocr).grid(row=1, column=0, sticky="w", padx=5, pady=5)

        ttk.Label(options_frame, text="PDF Engine:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        pdf_engine_combo = ttk.Combobox(options_frame, textvariable=self.pdf_engine, values=["fpdf"], state='readonly', width=10)
        pdf_engine_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # AI Configuration Section
        ai_frame = ttk.LabelFrame(self.master, text="AI Configuration")
        ai_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(ai_frame, text="AI Model:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ai_model_combo = ttk.Combobox(ai_frame, textvariable=self.ai_model, values=["gemini-2.0-flash-exp", "gemini-pro", "gemini-1.5-pro-latest"], state='readonly', width=20)
        ai_model_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(ai_frame, text="API Key:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(ai_frame, textvariable=self.api_key, width=30, show="*").grid(row=1, column=1, sticky="ew", padx=5, pady=5)  # Show="*" for password input

        # Output File Section
        output_frame = ttk.LabelFrame(self.master, text="Output Files")
        output_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(output_frame, text="Flashcard Data File Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(output_frame, textvariable=self.data_file, width=20).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(output_frame, text="Anki Deck File Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(output_frame, textvariable=self.anki_output, width=20).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Processing Button
        self.start_button = ttk.Button(self.master, text="Start Processing", command=self.start_processing)
        self.start_button.grid(row=4, column=0, pady=20, sticky="ew")

        # Crafted by Label (now a tk.Text widget)
        crafted_by_text = "Crafted by : Dr. Mahmoud Hamad\nA Plastic Surgeon\nhttps://www.instagram.com/mahmoud.aboulnasr/\nGithub: @x-cod3r"
        self.crafted_by_text_widget = tk.Text(self.master, height=4, wrap="word", borderwidth=0, highlightthickness=0)
        self.crafted_by_text_widget.insert(tk.END, crafted_by_text)

        # Create a clickable button at the location of the link
        start_pos = crafted_by_text.find("https://www.instagram.com/mahmoud.aboulnasr/")
        if start_pos != -1:
            end_pos = start_pos + len("https://www.instagram.com/mahmoud.aboulnasr/")
            self.crafted_by_text_widget.tag_configure("hyperlink", foreground="blue", underline=True)
            self.crafted_by_text_widget.window_create(f"1.{start_pos}", window=tk.Button(self.crafted_by_text_widget, text="https://www.instagram.com/mahmoud.aboulnasr/", cursor="hand2", relief="flat", borderwidth=0, font=("TkDefaultFont", 10, "underline"), foreground="blue", command=self.open_hyperlink))
            self.crafted_by_text_widget.tag_add("hyperlink", f"1.{start_pos}", f"1.{end_pos}")
            self.crafted_by_text_widget.config(cursor="arrow")

        self.crafted_by_text_widget.config(state="disabled")  # Make text read-only
        self.crafted_by_text_widget.grid(row=5, column=0, pady=10, sticky="s")

        # Make columns in input and options sections resize with window
        input_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(1, weight=1)
        ai_frame.columnconfigure(1, weight=1)
        output_frame.columnconfigure(1, weight=1)

    def browse_files(self):
        input_path = filedialog.askopenfilename(title="Select a file or directory")
        if input_path:
            self.input_path.set(input_path)

    def start_processing(self):
        input_path = self.input_path.get()
        if not input_path:
            messagebox.showerror("Error", "Please select a file or directory.")
            return

        try:
            pages_per_pdf = int(self.pages_per_pdf.get())
        except ValueError:
            messagebox.showerror("Error", "Pages per PDF must be a valid number")
            return

        use_ocr = self.use_ocr.get()
        pdf_engine = self.pdf_engine.get()
        data_file = self.data_file.get()
        anki_output = self.anki_output.get()
        ai_model = self.ai_model.get()
        api_key = self.api_key.get()
        # Configure API key for each process
        genai.configure(api_key=api_key)
        # Disable the start button to avoid double clicks
        self.start_button.config(state=tk.DISABLED)
        Thread(target=self.run_processing, args=(input_path, pages_per_pdf, use_ocr, pdf_engine, data_file, anki_output, ai_model, api_key)).start()

    def run_processing(self, input_path, pages_per_pdf, use_ocr, pdf_engine, data_file, anki_output, ai_model, api_key):
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        logging.info(f"Temporary directory created: {temp_dir}")

        try:
            # 1. Process files into PDFs
            logging.info("Starting PDF processing...")
            process_files(input_path, temp_dir, pages_per_pdf, use_ocr, pdf_engine)
            logging.info("PDF processing complete.")

            # 2. Generate Flashcards from PDFs and save to text file
            pdf_files = [file for file in Path(temp_dir).glob("*.pdf")]
            if pdf_files:
                self.pending_chats = len(pdf_files)  # Update the counter of open chats.
                for pdf_file in pdf_files:
                    logging.info(f"Found PDF for chat: {pdf_file}")
                    self.master.after(0, self.open_chat_window, str(pdf_file), os.path.join(temp_dir, data_file), os.path.join(temp_dir, anki_output), ai_model, api_key)  # Use master after
            else:
                logging.warning("No PDF files to process.")

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            self.start_button.config(state=tk.NORMAL)  # Re-enable button regardless of success/failure

    def open_chat_window(self, pdf_file, data_file, anki_output, ai_model, api_key):
        logging.info(f"Opening chat window for pdf: {pdf_file}, data file: {data_file}, model: {ai_model}, api_key:{api_key}")
        if pdf_file not in self.chat_windows or not tk.Toplevel.winfo_exists(self.chat_windows.get(pdf_file)):
            chat_window = tk.Toplevel(self.master)
            chat_window.title(f"Chat for {Path(pdf_file).name}")
            chat_window.geometry("400x350")  # increase the height to have space for the progress bar
            self.chat_windows[pdf_file] = chat_window
            chat_window.columnconfigure(0, weight=1)
            ttk.Label(chat_window, text="Number of Flashcards:", anchor="center").pack(pady=5)
            num_cards_entry = ttk.Entry(chat_window)
            num_cards_entry.pack(pady=5)

            self.progress_bar = ttk.Progressbar(chat_window, orient="horizontal", length=300, mode="determinate")
            self.progress_bar.pack(pady=10, fill="x", padx=20)  # Make the progress bar expand with the window

            done_command = functools.partial(self.close_chat_window, chat_window, data_file, anki_output)
            self.generate_button = ttk.Button(chat_window, text="Generate Flashcards", command=lambda: self.generate_flashcards(chat_window, num_cards_entry, pdf_file, data_file, ai_model, api_key))
            self.generate_button.pack(pady=10)
            self.done_button = ttk.Button(chat_window, text="Done", command=done_command)
            self.done_button.pack(pady=10)
        else:
            self.chat_windows.get(pdf_file).lift()

    def generate_flashcards(self, chat_window, num_cards_entry, pdf_file, data_file, ai_model, api_key):
        logging.info(f"Generating flashcards for pdf: {pdf_file}, data_file:{data_file}, model: {ai_model}, api_key:{api_key}")
        try:
            num_cards = int(num_cards_entry.get())
            if num_cards <= 0:
                messagebox.showerror("Error", "Number of cards must be a positive number")
                return
        except ValueError:
            messagebox.showerror("Error", "Number of cards must be a valid integer")
            return
        self.generate_button.config(state=tk.DISABLED)  # Disable the generate button
        self.done_button.config(state=tk.DISABLED)  # Disable the done button
        logging.info(f"Extracting text from pdf: {pdf_file}")
        pdf_text = extract_text_from_pdf_no_ocr(pdf_file)
        logging.info(f"Text extracted: {pdf_text[:200]}...")
        prompt = f"Create {num_cards} flashcards that cover the main topics and core concepts of the document and rational reasoning between facts and concepts. Each flashcard should contain a question with the word Front before it and the corresponding answer immediately after on the next line with the word Back before it and print the flashcards only as the format Front  <question> Back  <answer>."
        logging.info(f"Generating response with prompt: {prompt}")
        # Configure API key for each prompt
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(ai_model)
        self.progress_bar["maximum"] = num_cards  # Set the maximum to the number of cards
        response_text = chat_with_pdf(prompt, pdf_text, model)
        self.progress_bar["value"] = num_cards  # Make the progress bar go to full
        chat_window.update()  # Update the GUI
        from workflow_utils import save_response_to_file
        logging.info(f"Saving response to data file: {data_file}")
        save_response_to_file(response_text, data_file)
        logging.info(f"Flashcards appended to data file and chat window closed.")
        self.generate_button.config(state=tk.NORMAL)  # Enable the generate button
        self.done_button.config(state=tk.NORMAL)  # Enable the done button

    def close_chat_window(self, chat_window, data_file, anki_output):
        chat_window.destroy()
        self.pending_chats -= 1
        if self.pending_chats == 0:
            self.wait_for_chats(data_file, anki_output)

    def wait_for_chats(self, data_file_path, anki_output_path):
        while self.pending_chats > 0:
            time.sleep(0.1)
            self.master.update()  # Keep GUI responsive while waiting.
        # 3. Create Anki Deck after all chats are complete
        logging.info("Creating Anki deck...")
        create_anki_deck(data_file_path, anki_output_path)
        logging.info(f"Anki deck creation complete. Check '{anki_output_path}'.")
        # Move files to the permanent location (Documents/AnkiDecks)
        self.move_files_to_permanent_location(anki_output_path)
        messagebox.showinfo("Success", "Processing complete")

    def move_files_to_permanent_location(self, anki_output_path):
        """
        Move the Anki deck and processed files to the Documents/AnkiDecks folder.
        """
        try:
            # Get the user's Documents directory
            documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
            anki_decks_dir = os.path.join(documents_dir, "AnkiDecks")
            os.makedirs(anki_decks_dir, exist_ok=True)

            # Move the Anki deck
            anki_deck_name = os.path.basename(anki_output_path)
            shutil.move(anki_output_path, os.path.join(anki_decks_dir, anki_deck_name))

            logging.info(f"Anki deck moved to: {anki_decks_dir}")
        except Exception as e:
            logging.error(f"Error moving files: {e}")
            messagebox.showerror("Error", f"Error moving files: {e}")

    def open_hyperlink(self):
        webbrowser.open("https://www.instagram.com/mahmoud.aboulnasr/")

if __name__ == "__main__":
    root = tk.Tk()
    app_gui = AppGUI(root)
    root.mainloop()