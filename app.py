import numpy as np
import dimod
from dwave.system import EmbeddingComposite, DWaveSampler
from flask import Flask, request, jsonify
import spacy

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

def generate_schedule(num_full_time, num_part_time, min_wage, increase_rate):
    employees = ['emp_{}'.format(i) for i in range(num_full_time + num_part_time)]
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    shifts = ['morning', 'afternoon', 'evening']
    time_slots = len(days) * len(shifts)

    availability_matrix = np.ones((len(employees), time_slots))

    np.random.seed(0)
    for i in range(num_full_time, num_full_time + num_part_time):
        unavailable_slots = np.random.choice(time_slots, size=time_slots // 2, replace=False)
        availability_matrix[i, unavailable_slots] = 0

    delivery_cost_matrix = np.random.randint(1, 10, (time_slots,))

    future_min_wage = min_wage * ((1 + increase_rate / 100) ** 1)
    overtime_rate = 1.5 * future_min_wage

    hours_per_week = 40
    total_full_time_cost = num_full_time * hours_per_week * future_min_wage
    total_part_time_cost = num_part_time * (hours_per_week / 2) * future_min_wage
    total_cost_constraint = total_full_time_cost + total_part_time_cost

    def calculate_overtime_cost(hours_worked, future_min_wage, overtime_rate):
        regular_hours = min(hours_worked, 40)
        overtime_hours = max(hours_worked - 40, 0)
        return regular_hours * future_min_wage + overtime_hours * overtime_rate

    def create_bqm(emp_availability, delivery_costs, total_cost_constraint, future_min_wage, overtime_rate):
        bqm = dimod.BinaryQuadraticModel('BINARY')
        
        for i in range(len(employees)):
            for j in range(time_slots):
                bqm.add_variable(f'emp_{i}_{j}', -emp_availability[i, j])
        
        for j in range(time_slots):
            bqm.add_variable(f'del_{j}', -delivery_costs[j])
        
        for i in range(len(employees)):
            for d in range(len(days)):
                bqm.add_linear_equality_constraint(
                    [(f'emp_{i}_{d*3 + s}', 1) for s in range(len(shifts))],
                    constant=-1,
                    lagrange_multiplier=10.0
                )
        
        total_hours = sum(emp_availability[i, j] for i in range(len(employees)) for j in range(time_slots))
        total_hours_constraint = total_hours * future_min_wage
        bqm.add_linear_inequality_constraint(
            [(f'emp_{i}_{j}', 1) for i in range(len(employees)) for j in range(time_slots)],
            constant=-total_cost_constraint,
            lagrange_multiplier=10.0
        )
        
        for i in range(len(employees)):
            hours_worked = sum(emp_availability[i, j] for j in range(time_slots))
            overtime_cost = calculate_overtime_cost(hours_worked, future_min_wage, overtime_rate)
            bqm.add_linear_inequality_constraint(
                [(f'emp_{i}_{j}', 1) for j in range(time_slots)],
                constant=-overtime_cost,
                lagrange_multiplier=10.0
            )

        return bqm

    bqm = create_bqm(availability_matrix, delivery_cost_matrix, total_cost_constraint, future_min_wage, overtime_rate)
    sampler = EmbeddingComposite(DWaveSampler())
    response = sampler.sample(bqm, num_reads=100)

    emp_schedule = {emp: [] for emp in employees}
    delivery_schedule = {}
    for i in range(len(employees)):
        for j in range(time_slots):
            if response.first.sample[f'emp_{i}_{j}'] == 1:
                emp_schedule[employees[i]].append((days[j // 3], shifts[j % 3]))

    for j in range(time_slots):
        if response.first.sample[f'del_{j}'] == 1:
            delivery_schedule[(days[j // 3], shifts[j % 3])] = delivery_cost_matrix[j]

    return emp_schedule, delivery_schedule

@app.route('/schedule', methods=['POST'])
def schedule():
    data = request.json
    try:
        num_full_time = int(data['num_full_time'])
        num_part_time = int(data['num_part_time'])
        min_wage = float(data['min_wage'])
        increase_rate = float(data['increase_rate'])

        if num_full_time <= 0 or num_part_time <= 0 or min_wage <= 0 or increase_rate < 0:
            return jsonify({"error": "Invalid input values"}), 400

        emp_schedule, delivery_schedule = generate_schedule(num_full_time, num_part_time, min_wage, increase_rate)
        return jsonify({"employee_schedule": emp_schedule, "delivery_schedule": delivery_schedule})
    except (ValueError, KeyError) as e:
        return jsonify({"error": "Invalid input data"}), 400

@app.route('/event', methods=['POST'])
def event():
    data = request.json
    event_description = data.get('event_description', '')

    doc = nlp(event_description)
    affected_employees = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']

    employees = ['emp_{}'.format(i) for i in range(10)]
    for emp in affected_employees:
        if emp in employees:
            emp_index = employees.index(emp)
            availability_matrix[emp_index, :] = 0

    bqm = create_bqm(availability_matrix, delivery_cost_matrix, total_cost_constraint, future_min_wage, overtime_rate)
    response = sampler.sample(bqm, num_reads=100)
    emp_schedule, delivery_schedule = parse_response(response)

    return jsonify({"employee_schedule": emp_schedule, "delivery_schedule": delivery_schedule})

def parse_response(response):
    emp_schedule = {emp: [] for emp in employees}
    delivery_schedule = {}
    for i in range(len(employees)):
        for j in range(time_slots):
            if response.first.sample[f'emp_{i}_{j}'] == 1:
                emp_schedule[employees[i]].append((days[j // 3], shifts[j % 3]))

    for j in range(time_slots):
        if response.first.sample[f'del_{j}'] == 1:
            delivery_schedule[(days[j // 3], shifts[j % 3])] = delivery_cost_matrix[j]

    return emp_schedule, delivery_schedule

if __name__ == "__main__":
    app.run(debug=True)