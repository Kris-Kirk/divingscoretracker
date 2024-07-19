from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        event_date = request.form['date']
        event_number = request.form['event_number']
        with open('log.txt', 'a') as f:
            f.write(f"Event Date: {event_date}, Event Number: {event_number}\n")
        
        session['date'] = event_date
        session['event_number'] = event_number
        return redirect(url_for('divers_route'))
    return render_template('setup.html')

@app.route('/divers', methods=['GET', 'POST'])
def divers_route():
    global divers
    if request.method == 'POST':
        diver_name = request.form['diver_name']
        if diver_name:
            divers.append(diver_name)
            with open('log.txt', 'a') as f:
                f.write(f"Diver: {diver_name}\n")
        return redirect(url_for('divers_route'))
    return render_template('divers.html', divers=divers)

@app.route('/judges', methods=['GET', 'POST'])
def judges():
    if request.method == 'POST':
        num_judges = int(request.form['num_judges'])
        session['num_judges'] = num_judges
        return redirect(url_for('submit_scores'))
    return render_template('judges.html')

@app.route('/submit_scores', methods=['GET', 'POST'])
def submit_scores():
    global divers, scores, history, redo_history, current_diver_index, current_round
    num_judges = session.get('num_judges', 3)
    if request.method == 'POST':
        diver = request.form['diver']
        dd = float(request.form['dd'])
        judge_scores = [float(request.form[f'judge{i+1}']) for i in range(num_judges)]
        
        history.append((diver, scores.get(diver, 0)))
        redo_history.clear()
        
        if num_judges == 5:
            judge_scores.remove(max(judge_scores))
            judge_scores.remove(min(judge_scores))
        
        total_score = sum(judge_scores) * dd
        scores[diver] = scores.get(diver, 0) + total_score
        
        with open('log.txt', 'a') as f:
            f.write(f"Diver: {diver}, DD: {dd}, Scores: {judge_scores}, Total: {total_score}\n")
        
        # Move to the next diver
        current_diver_index = (current_diver_index + 1) % len(divers)
        if current_diver_index == 0:
            current_round += 1
        
        return redirect(url_for('submit_scores'))
    
    return render_template('submit_scores.html', divers=divers, num_judges=num_judges, scores=scores, current_diver_index=current_diver_index, current_round=current_round)

@app.route('/rankings')
def rankings():
    sorted_divers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return render_template('rankings.html', sorted_divers=sorted_divers)

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
    global divers, scores, history, redo_history, current_diver_index, current_round, last_selected_diver
    divers = []
    scores = {}
    history = []
    redo_history = []
    current_diver_index = 0
    current_round = 1
    last_selected_diver = None
    return redirect(url_for('setup'))

if __name__ == '__main__':
    app.run(debug=True)
