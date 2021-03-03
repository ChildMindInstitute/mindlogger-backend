<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>Hello ${userToInvite['firstName']},</p>

    <p>
    <b>${user['firstName']} (${user['login']})</b> has invited
    you to join the <b>${group['name']}</b> group! To join the group,
    <a href="${host}#group/${group['_id']}">click here</a> and then click
    "Join group".
    </p>
</div>

<%include file="_footer.en.mako"/>
