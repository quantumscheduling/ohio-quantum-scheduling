let employeeCount = 2;

function addEmployeeField() {
    employeeCount++;
    const employeeDiv = document.createElement('div');
    employeeDiv.innerHTML = `
        <label for="emp_${employeeCount - 1}">Employee ${employeeCount}:</label>
        <input type="text" id="emp_${employeeCount - 1}" name="emp_${employeeCount - 1}" required>
    `;
    document.getElementById('employee-names').appendChild(employeeDiv);
}

document.getElementById('employee-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const employeeNames = {};
    for (let i = 0; i < employeeCount; i++) {
        const empName = document.getElementById(`emp_${i}`).value;
        employeeNames[`emp_${i}`] = empName;
    }

    localStorage.setItem('employeeNames', JSON.stringify(employeeNames));
    document.getElementById('employee-form').style.display = 'none';
    document.getElementById('scheduling-form').style.display = 'block';
});

document.getElementById('scheduling-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const numFullTime = parseInt(document.getElementById('num-full-time').value);
    const numPartTime = parseInt(document.getElementById('num-part-time').value);
    const minWage = parseFloat(document.getElementById('min-wage').value);
    const increaseRate = parseFloat(document.getElementById('increase-rate').value);

    if (isNaN(numFullTime) || numFullTime <= 0 || isNaN(numPartTime) || numPartTime <= 0 ||
        isNaN(minWage) || minWage <= 0 || isNaN(increaseRate) || increaseRate < 0) {
        alert('Please enter valid input values.');
        return;
    }

    const data = {
        num_full_time: numFullTime,
        num_part_time: numPartTime,
        min_wage: minWage,
        increase_rate: increaseRate
    };

    fetch('/schedule', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(schedule => {
        if (schedule.error) {
            alert(schedule.error);
        } else {
            displaySchedule(schedule);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while generating the schedule.');
    });
});

document.getElementById('event-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const storeEvent = document.getElementById('store-event').value;

    const data = {
        event_description: storeEvent
    };

    document.getElementById('event-feedback').textContent = 'Analyzing event...';

    fetch('/event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.error) {
            alert(result.error);
        } else {
            document.getElementById('event-feedback').textContent = 'Event analysis complete. Schedule updated.';
            displaySchedule(result.schedule);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while analyzing the event.');
    });
});

function displaySchedule(schedule) {
    const outputDiv = document.getElementById('schedule-output');
    outputDiv.innerHTML = '';

    const table = document.createElement('table');
    table.classList.add('schedule-table');

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headerRow.innerHTML = '<th>Employee</th><th>Schedule</th>';
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    const employeeNames = JSON.parse(localStorage.getItem('employeeNames'));
    for (const [employee, shifts] of Object.entries(schedule.employee_schedule)) {
        const row = document.createElement('tr');
        const employeeCell = document.createElement('td');
        employeeCell.textContent = employeeNames[employee] || employee;
        const shiftsCell = document.createElement('td');
        shiftsCell.textContent = shifts.join(', ');
        row.appendChild(employeeCell);
        row.appendChild(shiftsCell);
        tbody.appendChild(row);
    }

    table.appendChild(tbody);
    outputDiv.appendChild(table);
}