(function ($) {
    "use strict";
    $(document).ready(function () {
        $('.displaytools').click(function () {
            $('.utilities').slideToggle();
        });
        if ($('#wizard').length) {
            $('#wizard').smartWizard();
            $('#wizard_verticle').smartWizard({
                transitionEffect: 'slide'
            });
            $('.buttonNext').addClass('btn btn-success');
            $('.buttonPrevious').addClass('btn btn-primary');
            $('.buttonFinish').addClass('btn btn-default');

        } else {
            console.log('wizard not find!');
        }
        if ($('#task_name').length) {
            validateTaskName();
        }
        if ($('#step-3').length || $('#step-4').length || $('#step-5').length) {
            stepactive();
        }
        connectors_breadCrumbs();

        //stepactive();

    })
    $(window).load(function () {
        if ($('#wizard .actionBar').length) {
            $('#wizard .actionBar').remove();
        }

    });
})(jQuery)
function validateTaskName() {
    if ($('#task_name').val() === '') {
        $('.name_task .buttonNext').addClass('buttonDisabled');
    }
    $('#task_name').keyup(function () {
        if ($('#task_name').val() === '') {
            $('.name_task .buttonNext').addClass('buttonDisabled');
        } else {
            $('.name_task .buttonNext').removeClass('buttonDisabled');
        }
    });
}
function nextStep() {
    var sth = $('#step-2').height();
    $('#step-1').hide();
    $('.stepContainer').height(sth);
    $('#step-2').show();
    $('#l-step-2').removeClass('disabled');
    $('#l-step-2').addClass('selected');
    $('#l-step-1').removeClass('selected');
    $('#l-step-1').addClass('disabled');
}
function previusStep() {
    var soh = $('#step-1').height();
    $('#step-2').hide();
    $('.stepContainer').height(soh);
    $('#step-1').show();
    $('#l-step-1').removeClass('disabled');
    $('#l-step-1').addClass('selected');
    $('#l-step-2').removeClass('selected');
    $('#l-step-2').addClass('disabled');
}
function stepactive() {
    var lstnum = '';
    var active = '';
    var daid = '';
    $('.steps').each(function () {
        var dah = '';
        var st = $(this).data('status');
        if (st == 'active') {
            $(this).show();
            dah = $(this).height();
            if (dah < '100') {
                dah = '200';
                $('.stepContainer').height(dah);
            } else {
                $('.stepContainer').height(dah);
            }
            active = $(this).data('step');
        } else {

            $(this).hide();
        }
    });
    $('.stlink').each(function () {
        lstnum = $(this).data('step');
        if (lstnum == active) {
            $(this).removeClass('disabled');
            $(this).addClass('selected');
        } else {
            $(this).removeClass('selected');
            $(this).addClass('disabled');
        }
    });
}
function connectors_breadCrumbs() {
    var gsrc = $('.source_name').html();
    $('.connectors-way').html(gsrc);
    $('.nav.side-menu > li').removeClass('active');
    $('.connectors-way').addClass('active');
    $('.nav.child_menu').hide();
    $('.connectors-way').find('.nav.child_menu').slideToggle('slow');
    $('.connectors-way').click(function () {
        $('.nav.side-menu > li').removeClass('active');
        $(this).addClass('active');
        $('.nav.child_menu').hide();
        $(this).find('.nav.child_menu').slideToggle('slow');
    });
}