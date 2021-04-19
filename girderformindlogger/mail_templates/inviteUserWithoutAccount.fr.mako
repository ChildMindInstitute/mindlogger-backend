## -*- coding: utf-8 -*-
<%include file="_header.mako"/>

<div style="max-width: 440px;">
    <p>
        Bonjour ${userName}!
    </p>

    <p>
        Vous avez été invité par ${coordinatorName} à être un ${role} de l'applet "${appletName}" sur MindLogger.
    </p>

    <p>
        Veuillez vous rendre ici <a href="${url}">here</a> pour créer un nouveau compte et accepter l'invitation.
    </p>
</div>

<%include file="_footer.fr.mako"/>
