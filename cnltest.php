<?php

function base16Decode($arg){
	$ret='';
	for($i=0;$i<strlen($arg);$i+=2){
        $tmp = hexdec(substr($arg, $i, 2));
		$ret .= chr($tmp);

    }
	return $ret;
}

function base16Encode($arg)
{
    $ret='';
    for($i=0;$i<strlen($arg);$i++)
    {
        $tmp=ord(substr($arg,$i,1));
        $ret.=dechex($tmp);
    }
    return $ret;
}

$key='1234567890987654';
$transmitKey=base16Encode($key);
$link="http://rapidshare.com/files/285626259/jDownloader.dmg\r\nhttp://rapidshare.com/files/285622259/jDownloader2.dmg";
$cp = mcrypt_module_open(MCRYPT_RIJNDAEL_128, '', 'cbc', '');
@mcrypt_generic_init($cp, $key, $key);
$enc = mcrypt_generic($cp, $link);
mcrypt_generic_deinit($cp);
mcrypt_module_close($cp);
$crypted=base64_encode($enc);

echo $crypted, PHP_EOL;

$crypted = 'DRurBGEf2ntP7Z0WDkMP8e1ZeK7PswJGeBHCg4zEYXZSE3Qqxsbi5EF1KosgkKQ9SL8qOOUAI+eDPFypAtQS9A==';
$cp = mcrypt_module_open(MCRYPT_RIJNDAEL_128, '', 'cbc', '');
$enc=base64_decode($crypted);
$decrypt_key = base16Decode($transmitKey);
@mcrypt_generic_init($cp, $decrypt_key, $decrypt_key);
$dec = mdecrypt_generic($cp, $enc);

mcrypt_generic_deinit($cp);
mcrypt_module_close($cp);

echo $dec, PHP_EOL;