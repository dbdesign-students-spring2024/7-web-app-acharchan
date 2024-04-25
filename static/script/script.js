function add_todo(){

    var user_input_element = document.getElementById("todo-input");

    var user_input = user_input_element.value;

    var current_date = new Date();
    var day = current_date.getDate();
    var month = current_date.getMonth() + 1;
    var year = current_date.getFullYear();

    var formattedDate = (day < 10 ? '0' : '') + day + '-' + (month < 10 ? '0' : '') + month + '-' + year;

    if(user_input.trim().length > 0){

        var xhr = new XMLHttpRequest();

        var url = "http://localhost:5000/create_todo";

        var params = "todo=" + user_input + "&date=" + formattedDate;

        xhr.open("POST", url, true);

        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

        xhr.send(params)

    }

}