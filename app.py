from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
import os
import json
import uuid

app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'

DATA_DIR = 'static/data'
PROGRESS_FILE = 'progress.json'


def load_questions():
    tests = {}
    for test_dir in os.listdir(DATA_DIR):
        test_path = os.path.join(DATA_DIR, test_dir)
        if os.path.isdir(test_path):
            test_file = os.path.join(test_path, f'{test_dir.split()[0]}_data.txt')
            with open(test_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                questions = {}
                question = {}
                question_id = None
                for line in lines:
                    line = line.strip()
                    if line.startswith('Вопрос'):
                        if question_id and question:
                            questions[question_id] = question
                        question_id = f"{test_dir}_{line.split(' ')[1]}"
                        question = {'question': line, 'answers': [], 'correct': [], 'images': []}
                    elif line.startswith('- '):
                        question['answers'].append(line[2:].strip())
                    elif line.startswith('+ '):
                        question['answers'].append(line[2:].strip())
                        question['correct'].append(line[2:].strip())
                    elif line.startswith('img '):
                        question['images'].append(line[4:].strip())
                if question_id and question:
                    questions[question_id] = question
                tests[test_dir] = questions
    return tests


def load_progress():
    return session.get('progress', {})


def save_progress(progress):
    session['progress'] = progress


def reset_progress(testname):
    progress = load_progress()
    if testname in progress:
        del progress[testname]
    save_progress(progress)


questions_data = load_questions()


@app.route('/')
def index():
    return render_template('index.html', tests=questions_data.keys())


@app.route('/test/<test_name>')
def test(test_name):
    if test_name not in questions_data:
        return "Test not found", 404
    questions = list(questions_data[test_name].items())
    first_question_id = questions[0][0]
    return redirect(url_for('question', test_name=test_name, question_id=first_question_id))


@app.route('/question/<test_name>/<question_id>', methods=['GET', 'POST'])
def question(test_name, question_id):
    if test_name not in questions_data or question_id not in questions_data[test_name]:
        return "Question not found", 404

    question = questions_data[test_name][question_id]
    progress_data = load_progress()

    if request.method == 'POST':
        correct_answers = question['correct']
        answers = request.form.getlist('answers')
        if not answers:
            answers = [request.form.get('answer')]

        is_correct = all(answer in correct_answers for answer in answers) and len(answers) == len(correct_answers)
        progress_data[test_name] = progress_data.get(test_name, {})
        progress_data[test_name][question_id] = (answers, is_correct)
        save_progress(progress_data)

    next_question_id = None
    prev_question_id = None
    question_ids = list(questions_data[test_name].keys())
    current_index = question_ids.index(question_id)
    if current_index < len(question_ids) - 1:
        next_question_id = question_ids[current_index + 1]
    if current_index > 0:
        prev_question_id = question_ids[current_index - 1]

    result = progress_data.get(test_name, {}).get(question_id)
    return render_template('question.html', test_name=test_name, question=question, question_id=question_id,
                           next_question_id=next_question_id, prev_question_id=prev_question_id, result=result)


@app.route('/result/<test_name>')
def result(test_name):
    progress_data = load_progress()
    if test_name not in progress_data:
        return "No progress found for this test", 404
    results = progress_data[test_name]
    unanswered_questions = [q_id for q_id in questions_data[test_name].keys() if q_id not in results or not results[q_id][0]]
    if unanswered_questions:
        return render_template('unanswered.html', test_name=test_name, unanswered_questions=unanswered_questions)
    return render_template('result.html', test_name=test_name, results=results, questions=questions_data[test_name])


@app.route('/reset/<test_name>')
def reset(test_name):
    reset_progress(test_name)
    return redirect(url_for('index'))


if __name__ == '__main__':
    Session(app)
    app.run(debug=True)
