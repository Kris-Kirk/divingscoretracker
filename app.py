from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Initial Data
divers = []
scores = {}
history = []
redo_history = []
current_diver_index = 0
current_round = 1
last_selected_diver = None

diver_information = {}

undo_stack = []
redo_stack = []
global file_name

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global file_name
    if request.method == 'POST':
        event_date = request.form['date']
        event_number = request.form['event_number']
        file_name = f"{event_date}_Event_{event_number}.txt"
        with open(file_name, 'a') as f:
            f.write(f"Event Date: {event_date}, Event Number: {event_number}\n")
        
        # print(f"Event Date: {event_date}, Event Number: {event_number}")
        
        # with open('log.txt', 'a') as f:
        #     f.write(f"\nEvent Date: {event_date}, Event Number: {event_number}\n")
        
        session['date'] = event_date
        session['event_number'] = event_number
        return redirect(url_for('divers_route'))
    return render_template('setup.html')

@app.route('/divers', methods=['GET', 'POST'])
def divers_route():
    global divers, file_name
    if request.method == 'POST':
        diver_name = request.form['diver_name']
        event_date = session.get('date')
        event_number = session.get('event_number')
        
        if diver_name:
            divers.append(diver_name)
            diver_information[diver_name] = [] # TODO: Test this
            with open(file_name, 'a') as f:
                f.write(f"Diver: {diver_name}\n")
        return redirect(url_for('divers_route'))
    return render_template('divers.html', divers=divers)

@app.route('/remove_diver/<diver>')
def remove_diver(diver):
    print(f"Attempting to remove diver: {diver}")
    print(f"Current divers list: {divers}")
    if diver in divers:
        divers.remove(diver)
        session['divers'] = divers
        print(f"Diver {diver} removed. Updated divers list: {divers}")
        scores = session.get('scores', {})
        if diver in scores:
            del scores[diver]
        session['scores'] = scores
        undo_stack.append(('remove_diver', diver))
    else:
        print(f"Diver {diver} not found in divers list.")
    return redirect(url_for('divers_route'))



@app.route('/judges', methods=['GET', 'POST'])
def judges():
    if request.method == 'POST':
        num_judges = int(request.form['num_judges'])
        session['num_judges'] = num_judges
        return redirect(url_for('submit_scores'))
    return render_template('judges.html')

@app.route('/submit_scores', methods=['GET', 'POST'])
def submit_scores():
    global divers, scores, history, redo_history, current_diver_index, current_round, file_name
    num_judges = session.get('num_judges', 3)
    if request.method == 'POST':
        diver = request.form['diver']
        dd = float(request.form['dd'])
        judge_scores = [0] * num_judges
        
        for i in range(num_judges):
            score = request.form[f'judge{i+1}']
            if score == '1-' or score == '1+':
                score = 1.5
            elif score == '2-' or score == '2+':
                score = 2.5
            elif score == '3-' or score == '3+':
                score = 3.5
            elif score == '4-' or score == '4+':
                score = 4.5
            elif score == '5-' or score == '5+':
                score = 5.5
            elif score == '6-' or score == '6+':
                score = 6.5
            elif score == '7-' or score == '7+':
                score = 7.5
            elif score == '8-' or score == '8+':
                score = 8.5
            elif score == '9-' or score == '9+':
                score = 9.5
            else:
                score = float(score)
            judge_scores[i] = score
        
        history.append((diver, scores.get(diver, 0)))
        redo_history.clear()

        full_scores = judge_scores.copy()
        
        if num_judges == 5:
            judge_scores.remove(max(judge_scores))
            judge_scores.remove(min(judge_scores))
        
        total_score = sum(judge_scores) * dd
        scores[diver] = scores.get(diver, 0) + total_score
        
        with open(file_name, 'a') as f:
            f.write(f"Diver: {diver}, DD: {dd}, Scores: {judge_scores}, Total: {total_score}\n")

        diver_information[diver].append((dd, full_scores, total_score, scores[diver]))
        
        # Move to the next diver
        current_diver_index = (current_diver_index + 1) % len(divers)
        if current_diver_index == 0:
            current_round += 1
            with open(file_name, 'a') as f:
                f.write(f"Round: {current_round}\n")
        
        return redirect(url_for('submit_scores'))
    
    return render_template('submit_scores.html', divers=divers, num_judges=num_judges, scores=scores, current_diver_index=current_diver_index, current_round=current_round, diver_information=diver_information)

@app.route('/rankings')
def rankings():
    sorted_divers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    current_score = None
    current_place = 0
    next_place = 1

    ranked_divers = []

    for i, (diver, score) in enumerate(sorted_divers):
        if score != current_score:
            current_score = score
            current_place = next_place
        ranked_divers.append((current_place, diver, score))
        next_place += 1
    return render_template('rankings.html', ranked_divers=ranked_divers)

@app.route('/undo')
def undo():
    global history, scores, redo_history, current_diver_index, current_round, last_selected_diver
    if history:
        diver, previous_score = history.pop()
        redo_history.append((diver, scores.get(diver, 0)))
        scores[diver] = previous_score
        current_diver_index = (current_diver_index - 1) % len(divers)
        last_selected_diver = divers[current_diver_index]
        if current_diver_index == len(divers) - 1:
            current_round -= 1
    return redirect(url_for('submit_scores'))

@app.route('/redo')
def redo():
    global history, scores, redo_history, current_diver_index, current_round, last_selected_diver
    if redo_history:
        diver, previous_score = redo_history.pop()
        history.append((diver, scores.get(diver, 0)))
        scores[diver] = previous_score
        current_diver_index = (current_diver_index + 1) % len(divers)
        last_selected_diver = divers[current_diver_index]
        if current_diver_index == 0:
            current_round += 1
    return redirect(url_for('submit_scores'))

@app.route('/clear')
def clear():
    global divers, scores, history, redo_history, current_diver_index, current_round, last_selected_diver, diver_information
    divers = []
    scores = {}
    history = []
    redo_history = []
    diver_information = {}
    current_diver_index = 0
    current_round = 1
    last_selected_diver = None
    print("Diver_information: ", diver_information)
    return redirect(url_for('setup'))

@app.route('/download_log_file')
def download_log_file():
    diver_information_copy = {}
    round = 1
    event_number = session.get('event_number')
    pdf_filename = f"Event Date: {session.get('date')}, Event Number_{event_number}_Athlete_Scores.pdf"
    txt_filename = f"Event Date: {session.get('date')}, Event Number_{event_number}_Athlete_Scores.txt"
    diver_information_copy = diver_information.copy()
    print("Diver information copy: ", diver_information_copy)
    for diver, info in diver_information.items():
        try:
            data = info[-1][-1]
        except:
            del diver_information_copy[diver]
    
    with open(txt_filename, 'w') as f:
        f.write(f"{session.get('date')} Dive Meet, Event Number: {session.get('event_number')}\n")
        for diver, info in diver_information_copy.items():
            f.write(f"{diver}, Total: {info[-1][-1]:.2f}\n")
            round = 1
            for dd, scores, total, cum_total in info:
                f.write(f"#{round}, DD: {dd}, Scores: {scores}, Score: {total:.2f}, Total: {cum_total:.2f}\n")
                round += 1  
        f.write("\nPlacings:\n")
        # Sort divers by total score and write to file
        sorted_divers = sorted(diver_information_copy.items(), key=lambda x: x[1][-1][-1], reverse=True)
        
        current_score = None
        current_place = 0
        next_place = 1

        for i, (diver, info) in enumerate(sorted_divers):
            # Displays properly ties for first place
            if current_score == None:
                current_score = info[-1][-1]
            # Records ties for second place and beyond
            if info[-1][-1] != current_score:
                current_score = info[-1][-1]
                current_place = next_place
            f.write(f"{current_place}. {diver}, Total: {info[-1][-1]:.3f}\n")
            next_place += 1        
            
    with open(txt_filename, 'r') as f:
        data = f.read()
        
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    lines = data.splitlines()
    y_position = 750
    line_height = 20
    page_bottom_margin = 50
    
    for line in lines:
        if y_position <= page_bottom_margin:
            c.showPage()
            y_position = 750
        c.drawString(100, y_position, line)
        y_position -= line_height
    c.save()
    return send_file(pdf_filename, as_attachment=True)
    
if __name__ == '__main__':
    app.run(debug=True)