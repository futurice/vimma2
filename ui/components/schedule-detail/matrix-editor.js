(function() {
    var rowLabels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
            'Saturday', 'Sunday'],
        colLabels = (function() {
            var v = [], i;
            for (i = 0; i < 24; i++) {
                v.push(i + ':00 → ' + i + ':30');
                v.push(i + ':30 → ' + ((i+1) % 24) + ':00');
            }
            return v;
        })();

    Polymer({
        is: 'matrix-editor',

        properties: {
            matrix: {
                type: Array,
                notify: true,
                observer: '_matrixChanged'
            },

            // The matrix to display. Keeps changing during a mouse drag, but
            // ‘matrix’ is only overridden when the dragging ends.
            _viewMatrix: Array,

            // The row and column under the mouse, or null.
            _hoverRow: {
                type: Number,
                value: null
            },
            _hoverCol: {
                type: Number,
                value: null
            },

            _editing: {
                type: Boolean,
                value: false
            },
            _startRow: {
                type: Number,
                value: null
            },
            _startCol: {
                type: Number,
                value: null
            }
        },

        _matrixChanged: function(newV, oldV) {
            console.log("matrixChanged",newV,oldV,typeof(newV));
            this._viewMatrix = clone(newV);
        },

        _cellClass: function(row, col, viewMatrix, editing) {
            var v = [];

            if (viewMatrix[row][col]) {
                v.push('on');
            } else {
                v.push('off');
            }

            var minR = Math.min(this._startRow, this._hoverRow),
                maxR = Math.max(this._startRow, this._hoverRow),
                minC = Math.min(this._startCol, this._hoverCol),
                maxC = Math.max(this._startCol, this._hoverCol);

            if (editing && minR <= row && row <= maxR &&
                    minC <= col && col <= maxC) {
                v.push('dragging');
            } else {
                v.push('normal');
            }

            return v.join(' ');
        },

        _help: function(row, col) {
            if (row === null || col === null) {
                return 'Mouse over the matrix for help';
            }
            return rowLabels[row] + ': ' + colLabels[col];
        },

        _mouseLeave: function() {
            this._hoverRow = null;
            this._hoverCol = null;
        },
        _mouseOver: function(ev) {
            var row = ev.model.row, col = ev.model.col;
            this._hoverRow = row;
            this._hoverCol = col;
            if (this._editing) {
                this._dragTo(row, col);
            }
        },
        _mouseDown: function(ev) {
            if (!this._editing) {
                this._startEdit(ev.model.row, ev.model.col);
            }
        },
        _mouseUp: function(ev) {
            if (this._editing) {
                this._commitEdit();
            }
        },

        _startEdit: function(row, col) {
            if (this._editing) {
                throw 'Already editing';
            }

            this._viewMatrix = clone(this.matrix);

            this._editing = true;
            this._startRow = row;
            this._startCol = col;

            this._dragTo(row, col);
        },

        _dragTo: function(row, col) {
            if (!this._editing) {
                throw 'Not editing';
            }

            var m = clone(this.matrix),
                val = !m[this._startRow][this._startCol],
                rMin = Math.min(this._startRow, row),
                rMax = Math.max(this._startRow, row),
                cMin = Math.min(this._startCol, col),
                cMax = Math.max(this._startCol, col),
                i, j;
            for (i = rMin; i <= rMax; i++) {
                for (j = cMin; j <= cMax; j++) {
                    m[i][j] = val;
                }
            }
            this._viewMatrix = m;
        },

        _commitEdit: function() {
            if (!this._editing) {
                throw 'Not editing';
            }
            this._editing = false;
            this.matrix = clone(this._viewMatrix);
        }
    });
})();
