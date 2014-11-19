Polymer('human-time', {
    // shared array between component instances, but we never change it
    multiples: [
        {n: 60, name: 'm'},
        {n: 60, name: 'h'},
        {n: 24, name: 'day', sayplural: true},
        {n: 7, name: 'week', sayplural: true}
    ]
});
