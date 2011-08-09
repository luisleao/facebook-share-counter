var list = [];
var keys = [];

var xbees_list = [];
var xbees_keys = [];

var current_link = null;


$(document).ready(function(){
	get_all();
	
	$("#btn_update").click(function(e){
		e.preventDefault();
		get_all();
	});
	
	$("#btn_addlink").click(function(e){
		e.preventDefault();
		$(".shadow").fadeIn('slow', function() {
			$("#formulario").fadeIn('slow');
		});
	});

	$("#btn_submit").click(function(e){
		e.preventDefault();
		$.ajax({
			type: "POST",
			url: "/link/add/",
			data: $("#formulario form").serializeArray(),
			success: function(data) {
				if (!data.ok) {
					alert(data.mensagem);
					return;
				}
				$("#formulario").fadeOut('slow', function() {
					$(".shadow").fadeOut('slow');
					$("#formulario input").val("");
					get_links();
				});
				
			},
			error: function() {
				alert("Err sending data.");
			},
			dataType: "json"
		});
		
	});

	$("#btn_cancel").click(function(e){
		e.preventDefault();
		$("#formulario").fadeOut('slow', function() {
			$(".shadow").fadeOut('slow');
		});
	});
	$("#btn_close").click(function(e){
		e.preventDefault();
		current_link = null;
		$("#detalhe").fadeOut('slow', function() {
			$(".shadow").fadeOut('slow');
		});
	});
	
	setInterval(function() { get_all(); }, 10000);
});


function get_all() {
	get_links();
	get_xbees();
}


/* *** LINKS FUNCTIONS *** */
function get_links() {
	//console.debug("GET LINKS!");
	$.getJSON("/link/list/", function(links) {
		set_links(links);
	}, "text");
}
function set_links(links){
	$(links).each(function() {
		//if (!this)
		//	return;
		//alert($.inArray(this.key_name, keys));
		if ($.inArray(this.key_name, keys) < 0)
			keys.push(this.key_name);
		list[this.key_name] = this;
		add_link(this.key_name, this.url, this.name, this.shares, this.enabled);
	});
	calculate_link_percentage();

	if (!$(".links_grid").is(":visible"))
		$(".links_grid").fadeIn("slow");
		
		
	
}
function add_link(key_name, url, name, shares, enabled){
	if (!key_name)
		return;
		
	var link_layer = $("#links #link_" + key_name).first();
	if (link_layer.length == 0) {
		link_layer = $("#links .model").clone().removeClass("model");
		link_layer.attr("id", "link_" + key_name);
		link_layer.appendTo("#links");
		link_layer.children(".name").unbind().click(detail_link);
		link_layer.children(".delete").unbind().click(delete_link);
		link_layer.children(".status").unbind().click(status_link);
	}
	
	if (enabled && link_layer.hasClass("disabled")) {
		link_layer.removeClass("disabled");
	}
	if (!enabled && !link_layer.hasClass("disabled")) {
		link_layer.addClass("disabled");
	}
	
	//update shares
	link_layer.find(".count").html(shares==0 && "-" || shares);
	link_layer.find(".name").html(name);
	link_layer.find(".name").attr("title", url);

	link_layer.find(".status").html(enabled && "disable" || "enable");
	link_layer.find(".status").attr("title", enabled && "disable" || "enable");

	if (!link_layer.is(":visible"))
		link_layer.fadeIn();
	
}

function detail_link(e){
	e.preventDefault();
	var key_name = $(this).parent().attr("id").split("_")[1];
	var action = list[key_name].enabled && "disable" || "enable";

	current_link = key_name;

	$("#detalhe #xbees li").removeClass("bounded");
	$("#detalhe #xbees li .unbound").removeClass("show");
	$("#detalhe #xbees li .bound").removeClass("show");
	$("#detalhe #xbees li").show().not(".nolink").not(".link_" + key_name).hide();
	
	$("#detalhe #xbees li.link_" + key_name).addClass("bounded");
	$("#detalhe #xbees li.link_" + key_name).children(".unbound").addClass("show");
	$("#detalhe #xbees li.nolink").children(".bound").addClass("show");
	//$("#detalhe #xbees li.link_" + key_name).children(".bound").addClass("noshow");
	//$("#detalhe #xbees li.nolink").children(".unbound").addClass("noshow");
	
	//$("#detalhe #xbees li").show().not(".nolink").not(".link_95fbd09c80e50facc059419f178161dd").hide();
	
	$("#detalhe h3").html(list[key_name].name);
	$("#detalhe .link_url").html(list[key_name].url);

	$(".shadow").fadeIn('slow', function() {
		$("#detalhe").fadeIn('slow');
	});


}

function delete_link(e){
	e.preventDefault();
	var key_name = $(this).parent().attr("id").split("_")[1];
	if (confirm("Confirm delete of '"+list[key_name].name+"'?")) {
		$.getJSON("/link/delete/"+key_name+"/", function(data) {
			if (data.ok) {
				keys.splice(keys.indexOf(key_name), 1);
				$("#link_" + data.key_name).fadeOut('slow', function(){
					$(this).remove();
				});
			} else {
				alert(data.mensagem);
			}
		}, "text");
	}
}
function status_link(e){
	e.preventDefault();
	var key_name = $(this).parent().attr("id").split("_")[1];
	var action = list[key_name].enabled && "disable" || "enable";
	$.getJSON("/link/"+action+"/"+key_name+"/", function(data) {
		if (data.ok) {
			get_links();
		} else {
			alert(data.mensagem);
		}
	}, "text");
}



function calculate_link_percentage() {
	//var sum = 0;
	var max = 0;
	$(keys).each(function(index, value) {
		//sum += list[value].shares;
		if (list[value].shares > max)
			max = list[value].shares;
	});

	$(keys).each(function(index, value) {
		var percentage = Math.round(list[value].shares / max * 100 * .9);
		$("#links #link_" + value + " .index").animate({width: percentage+'%'}, 1500);
		$("#links #link_" + value + " .index").html("(" + percentage + "%)"); //.css("width", percentage + "%");
	});
	
}





/* *** XBEE FUNCTIONS *** */
function get_xbees() {
	//console.debug("GET XBEES!");
	$.getJSON("/xbee/list/", function(xbees) {
		set_xbees(xbees);
	}, "text");
}
function set_xbees(xbees) {
	$(xbees).each(function() {
		if (!this)
			return;
		//alert($.inArray(this.key_name, keys));
		if ($.inArray(this.key_name, xbees_keys) < 0)
			xbees_keys.push(this.key_name);
		xbees_list[this.key_name] = this;
		//alert(this.name);
		add_xbee(this.key_name, this.name, this.link, this.created, this.new);
	});
}
function add_xbee(key_name, name, link, created, is_new) {

	//"key_name": xbee.key().name(),
	//"name": xbee.address_l,
	//"link": xbee.link and xbee.link.key().name() or None,
	//"created": xbee.created.isoformat(),
	//"new": xbee.new


	if (!key_name)
		return;
		
	var xbee_layer = $("#detalhe #xbee_" + key_name).first();
	if (xbee_layer.length == 0) {
		xbee_layer = $("#detalhe .model").clone().removeClass("model");
		xbee_layer.attr("id", "xbee_" + key_name);
		xbee_layer.appendTo("#xbees");
		
		xbee_layer.children(".bound").unbind().click(bound_xbee);
		xbee_layer.children(".unbound").unbind().click(unbound_xbee);
	}

	xbee_layer.find(".name").html(name);
	xbee_layer.find(".name").attr("title", name);

	
	if (link)
		xbee_layer.removeClass().addClass("link_" + link)
	else
		xbee_layer.removeClass().addClass("nolink")

	if (is_new)
		xbee_layer.addClass("new");
	
	
	
	

	//link_layer.find(".status").html(enabled && "disable" || "enable");
	//link_layer.find(".status").attr("title", enabled && "disable" || "enable");
	

}


function bound_xbee(e) {
	e.preventDefault();
	if (!current_link)
		return;
		
	var key_name = $(this).parent().attr("id").split("_")[1];
	$.getJSON("/link/addxbee/"+current_link+"/"+key_name+"/", function(data) {
		if (data.ok) {
			$("#detalhe #xbee_" + data.key_name).removeClass("new").removeClass("nolink").addClass("link_" + current_link);
			$("#detalhe #xbee_" + data.key_name).children(".unbound").addClass("show");
			$("#detalhe #xbee_" + data.key_name).children(".bound").removeClass("show");
			$("#detalhe #xbee_" + data.key_name).addClass("bounded");
			
		} else {
			alert(data.mensagem);
		}
	}, "text");
}
function unbound_xbee(e) {
	e.preventDefault();
	if (!current_link)
		return;

	var key_name = $(this).parent().attr("id").split("_")[1];
	$.getJSON("/link/delxbee/"+current_link+"/"+key_name+"/", function(data) {
		if (data.ok) {
			$("#detalhe #xbee_" + data.key_name).removeClass("link_" + current_link).addClass("nolink");
			$("#detalhe #xbee_" + data.key_name).children(".unbound").removeClass("show");
			$("#detalhe #xbee_" + data.key_name).children(".bound").addClass("show");
			$("#detalhe #xbee_" + data.key_name).removeClass("bounded");
		} else {
			alert(data.mensagem);
		}
	}, "text");
}
