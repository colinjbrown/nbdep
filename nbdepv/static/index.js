define([
    'base/js/namespace',
    'jquery',
    'base/js/utils',
    'base/js/dialog'
], function(Jupyter, $, utils, dialog) {


    function onload() {

	    var nb = Jupyter.notebook;

	    //Init metadata
        nb.metadata.dependencies = nb.metadata.dependencies || [];

	    nb.events.on('kernel_ready.Kernel',function(event,data) {

	        var comm_manager = Jupyter.notebook.kernel.comm_manager;

	        var idx = nb.metadata.dependencies;
	        var session_id = Jupyter.notebook.kernel.id;

	        var currentdate = new Date();

	        var current_session = (currentdate.getMonth()+1)  + "/"
                + currentdate.getDate() + "/"
                + currentdate.getFullYear() + " @ "
                + currentdate.getHours() + ":"
                + currentdate.getMinutes() + ":"
                + currentdate.getSeconds();



	        var session_obj = {'session':session_id,'session_created':current_session,'deps':{}};
	        nb.metadata.dependencies.push(session_obj);

            var handle_msg=function(msg){
                console.log(msg);
                var data = msg.content.data;
                Object.keys(data).forEach(
                    function (key) {
                        session_obj.deps[key] = data[key];
                    }
                )
            };

            comm_manager.register_target('nbdepv', function(comm,msg){
                // register callback
                comm.on_msg(handle_msg)
            });

	        var text = '%load_ext nbdepv';
	        var callbacks = null;
	        var msg_id = nb.kernel.execute(text, callbacks, {silent: false, store_history: true,
            stop_on_error : true});
	        console.log(msg_id);
            console.log("Success");
        });
    }

    return {
	load_ipython_extension: onload
    };

});