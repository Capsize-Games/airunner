progress_html = '''
<div class="loader-container">
  <div class="loader"></div>
  <div class="progress-container">
    <progress value="*number*" max="100"></progress>
  </div>
  <span>*text*</span>
</div>
'''

css = '''
.loader-container {
  display: flex; /* Use flex to align items horizontally */
  align-items: center; /* Center items vertically within the container */
  white-space: nowrap; /* Prevent line breaks within the container */
}

.loader {
  border: 8px solid #f3f3f3; /* Light grey */
  border-top: 8px solid #3498db; /* Blue */
  border-radius: 50%;
  width: 30px;
  height: 30px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Style the progress bar */
progress {
  appearance: none; /* Remove default styling */
  height: 20px; /* Set the height of the progress bar */
  border-radius: 5px; /* Round the corners of the progress bar */
  background-color: #f3f3f3; /* Light grey background */
  width: 100%;
  vertical-align: middle !important;
}

/* Style the progress bar container */
.progress-container {
  margin-left: 20px;
  margin-right: 20px;
  flex-grow: 1; /* Allow the progress container to take up remaining space */
}

/* Set the color of the progress bar fill */
progress::-webkit-progress-value {
  background-color: #3498db; /* Blue color for the fill */
}

progress::-moz-progress-bar {
  background-color: #3498db; /* Blue color for the fill in Firefox */
}

/* Style the text on the progress bar */
progress::after {
  content: attr(value '%'); /* Display the progress value followed by '%' */
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white; /* Set text color */
  font-size: 14px; /* Set font size */
}

/* Style other texts */
.loader-container > span {
  margin-left: 5px; /* Add spacing between the progress bar and the text */
}

.no-generating-animation > .generating {
  display: none !important;
}

'''


def make_progress_bar_html(number, text):
    return progress_html.replace('*number*', str(number)).replace('*text*', text)


def make_progress_bar_css():
    return css
