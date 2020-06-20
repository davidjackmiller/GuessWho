// CONSTANTS
const facelessImageURL = "/static/img/faceless.jpg";

// GAME BOARD STORAGE
// 2D array of dicts ('flipped': bool, 'face': string)
var myCards = [];
// String of image url
var myTarget = '';
// 2D array of dicts ('flipped': bool)
var theirCards = [];
// Bool
var theyHaveTarget = false;

function updateGame(json) {
    console.log("Update game");
    if (Object.keys(json).length === 0) {
        console.log("Showing Settings Menu")
        $("#loadingIndicator").addClass('hidden');
        $("#settingsMenu").removeClass('hidden');
        $("#gameBoard").addClass('hidden');
    } else {
        console.log("Showing Game Board")
        storeGameBoard(json);
        populateGameBoard();
        $("#loadingIndicator").addClass('hidden');
        $("#settingsMenu").addClass('hidden');
        $("#gameBoard").removeClass('hidden');
    }
};

function displayFullGameError(destination_url) {
    window.alert("This game is full. Please try again later or try joining a different room. You'll be taken back to the home page now.")
    window.location.href = destination_url;
}

function setGameSettings() {
    console.log("setting game settings");
    // Get the settings from html
    var facepack = $('#facepacks_dropdown').val();
    var number_rows = $('#number_rows').val();
    var number_cols = $('#number_cols').val();
    // Communicate settings to server with socket
    data = {
        'room_id': room_id,
        'facepack': facepack,
        'rows': number_rows,
        'cols': number_cols,
    };
    console.log(data);
    socket.emit('game settings', data);
    // Stop the page from refreshing
    return false;
}

function storeGameBoard(json) {
    // Store the board
    myCards = json['myBoard']['cards'];
    theirCards = json['theirBoard']['cards'];
    myTarget = json['myBoard']['target'];
    theyHaveTarget = json['theirBoard']['has_target'];
    // Update the number of rows and columns
    document.documentElement.style.setProperty("--rowNum", myCards.length);
    document.documentElement.style.setProperty("--colNum", myCards[0].length);
}

function createCardForFace(face) {
    var div = $('<div></div>').addClass('card');
    // Image
    var img = $('<img id="dynamic">');
    img.addClass('faceImage');
    div.append(img);
    if (face) {
        img.attr('src', face);
        // Label
        var face_name = face.split('/').pop().split('.')[0];
        var label = $("<label>").text(face_name);
        label.addClass('cardLabel');
        div.append(label);
    } else {
        img.attr('src', facelessImageURL);
    }
    return div;
}

function createGridItemForCard(card, row, col) {
    var div = $('<div></div>').addClass('gridItem');
    var cardDiv = createCardForFace(card['face'], row, col);
    if (card['face']) {
        cardDiv.on('click', function() {
            faceTapped(row, col);
        });
    }
    if (card['flipped']) {
        div.addClass('flipped');
    }
    div.append(cardDiv);
    return div;
}

function createDivForTarget(target_chosen, face) {
    var div = $('<div></div>').addClass('targetCard');
    if (target_chosen) {
        var cardDiv = createCardForFace(face);
        div.append(cardDiv);
    } else {
        div.hide();
    }
    return div;
}

function populateGameBoard() {
    // Empty the game board
    $('#myBoard').empty();
    $('#theirBoard').empty();
    $('#myTarget').empty();
    $('#theirTarget').empty();
    // Player's cards
    myCards.forEach(function(row, r) {
        row.forEach(function(card, c) {
            var div = createGridItemForCard(card, r, c);
            $('#myBoard').append(div);
        });
    });
    // Opponent's cards
    theirCards.forEach(function(row, r) {
        row.forEach(function(card, c) {
            var div = createGridItemForCard(card, r, c);
            $('#theirBoard').append(div);
        });
    });
    // Create divs for target cards
    var iHaveTarget = myTarget.length !== 0;
    var myTargetDiv = createDivForTarget(iHaveTarget, myTarget);
    var theirTargetDiv = createDivForTarget(theyHaveTarget, "");
    $('#myTarget').append(myTargetDiv);
    $('#theirTarget').append(theirTargetDiv);
}

function faceTapped(row, col) {
    data = {
        'room_id': room_id,
        'row': row,
        'col': col,
    };
    if (myTarget.length === 0) {
        socket.emit('choose target', data);
    } else {
        socket.emit('flip card', data);
    }
}
