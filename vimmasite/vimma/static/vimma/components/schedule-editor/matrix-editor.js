Polymer('matrix-editor', {
    matrix: null,
    disabled: false,

    // the mouse is down and we're currently editing the matrix
    editing: false,
    // during edit mode this shows the matrix before we started editing
    prevMatrix: null,
    // the value to write while in edit mode
    writeVal: null,
    // the matrix cell where the edit drag operation started
    startRow: null,
    startCol: null,

    // during edit mode, the last matrix cell the mouse was dragged to. Allows
    // us to avoid recreating and redrawing the matrix if mouseOver fires on
    // the same cell while moving the mouse.
    lastDragRow: null,
    lastDragCol: null,

    startEdit: function(row, col) {
        if (this.editing) {
            throw 'Already editing';
        }
        if (this.disabled) {
            console.log('Schedule matrix is disabled, not starting edit');
            return;
        }
        this.editing = true;
        this.prevMatrix = clone(this.matrix);
        this.writeVal = !this.matrix[row][col];
        this.startRow = row;
        this.startCol = col;
        this.lastDragRow = null;
        this.lastDragCol = null;

        this.dragTo(row, col);
    },
    commitEdit: function() {
        this.editing = false;
        // force re-drawing of table to remove .highlight CSS class
        this.matrix = clone(this.matrix);
    },
    dragTo: function(row, col) {
        if (!this.editing) {
            throw 'Not in edit mode';
        }
        if (row == this.lastDragRow && col == this.lastDragCol) {
            return;
        }
        this.lastDragRow = row;
        this.lastDragCol = col;

        var m = clone(this.prevMatrix);
        var r, c,
            rMin = Math.min(this.startRow, row),
            rMax = Math.max(this.startRow, row),
            cMin = Math.min(this.startCol, col),
            cMax = Math.max(this.startCol, col);
        for (r = rMin; r <= rMax; r++) {
            for (c = cMin; c <= cMax; c++) {
                m[r][c] = this.writeVal;
            }
        }
        this.matrix = m;
    },

    mouseDown: function(ev, detail, sender) {
        if (!this.editing) {
            var row = parseInt(sender.getAttribute('row'), 10),
                col = parseInt(sender.getAttribute('col'), 10);
            this.startEdit(row, col);
        }
    },
    mouseUp: function(ev, detail, sender) {
        if (this.editing) {
            this.commitEdit();
        }
    },
    mouseOver: function(ev, detail, sender) {
        if (this.editing) {
            var row = parseInt(sender.getAttribute('row'), 10),
                col = parseInt(sender.getAttribute('col'), 10);
            this.dragTo(row, col);
        }
    },

    cellIsHighlighted: function(row, col) {
        if (!this.editing) {
            return false;
        }

        // min <= x <= max
        function between(x, v1, v2) {
            return (x-v1)*(x-v2) <= 0;
        }

        return between(row, this.startRow, this.lastDragRow) &&
            between(col, this.startCol, this.lastDragCol);
    }
});
