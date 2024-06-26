from flask import Flask, render_template, request, redirect, url_for
import os
import json

app = Flask(__name__)

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
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f)


def reset_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


questions_data = load_questions()
progress_data = load_progress()


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

    result = progress_data[test_name].get(question_id) if test_name in progress_data else None
    return render_template('question.html', test_name=test_name, question=question, question_id=question_id,
                           next_question_id=next_question_id, prev_question_id=prev_question_id, result=result)


@app.route('/result/<test_name>')
def result(test_name):
    if test_name not in progress_data:
        return "No progress found for this test", 404
    results = progress_data[test_name]
    return render_template('result.html', test_name=test_name, results=results, questions=questions_data[test_name])


@app.route('/reset/<test_name>')
def reset(test_name):
    reset_progress()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
